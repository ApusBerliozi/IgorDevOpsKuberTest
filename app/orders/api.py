"""HTTP API сервиса заказов.

POST /orders        — создать заказ (кладётся в очередь Redis)
GET  /orders/{id}   — статус заказа (pending -> processed | rejected)
GET  /healthz       — процесс жив
GET  /readyz        — процесс жив и Redis доступен
"""
import logging
import os
import uuid

import redis
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from orders import store

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("orders.api")

app = FastAPI(title="orders-api", version=os.environ.get("APP_VERSION", "dev"))

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = store.make_client()
    return _client


class OrderIn(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    qty: int = Field(gt=0, le=100)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": app.version}


@app.get("/readyz")
def readyz(r: redis.Redis = Depends(get_redis)):
    try:
        r.ping()
    except redis.RedisError as exc:
        log.error("redis is not available: %s", exc)
        raise HTTPException(status_code=503, detail="redis unavailable") from exc
    return {"status": "ready"}


@app.post("/orders", status_code=201)
def create_order(order: OrderIn, r: redis.Redis = Depends(get_redis)):
    order_id = uuid.uuid4().hex[:12]
    try:
        pipe = r.pipeline()
        pipe.hset(store.order_key(order_id), mapping={
            "sku": order.sku, "qty": order.qty, "status": "pending",
        })
        pipe.lpush(store.QUEUE_KEY, order_id)
        pipe.execute()
    except redis.RedisError as exc:
        log.error("failed to enqueue order: %s", exc)
        raise HTTPException(status_code=503, detail="storage unavailable") from exc
    log.info("order %s enqueued", order_id)
    return {"id": order_id, "status": "pending"}


@app.get("/orders/{order_id}")
def get_order(order_id: str, r: redis.Redis = Depends(get_redis)):
    try:
        data = r.hgetall(store.order_key(order_id))
    except redis.RedisError as exc:
        raise HTTPException(status_code=503, detail="storage unavailable") from exc
    if not data:
        raise HTTPException(status_code=404, detail="order not found")
    return {"id": order_id, **data}
