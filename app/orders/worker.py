"""Воркер: забирает заказы из очереди и проверяет их по каталогу.

Каталог целиком грузится в память при старте (так быстрее, чем ходить
в Redis за каждым товаром). Размер задаётся CATALOG_SIZE.
"""
import logging
import os
import signal
import sys
import time

import redis

from orders import store

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("orders.worker")

_running = True


def _stop(signum, _frame):
    global _running
    log.info("got signal %s, finishing current order and exiting", signum)
    _running = False


def load_catalog(size: int) -> dict[str, dict]:
    """Строит каталог товаров SKU-00000 ... SKU-{size-1}."""
    started = time.monotonic()
    catalog = {
        f"SKU-{i:05d}": {
            "name": f"Product #{i}",
            "price": round(1 + (i % 997) * 0.37, 2),
            "tags": [f"tag-{i % 13}", f"tag-{i % 17}", f"warehouse-{i % 5}"],
            "description": f"Описание товара {i}. " * 4,
        }
        for i in range(size)
    }
    log.info("catalog loaded: %d items in %.1fs", len(catalog), time.monotonic() - started)
    return catalog


def process(r: redis.Redis, catalog: dict, order_id: str) -> str:
    key = store.order_key(order_id)
    order = r.hgetall(key)
    if not order:
        log.warning("order %s disappeared", order_id)
        return "missing"
    status = "processed" if order.get("sku") in catalog else "rejected"
    r.hset(key, "status", status)
    log.info("order %s -> %s", order_id, status)
    return status


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    catalog = load_catalog(int(os.environ.get("CATALOG_SIZE", "1000")))

    r = store.make_client()
    try:
        r.ping()
    except redis.RedisError as exc:
        log.error("cannot connect to redis: %s", exc)
        return 1
    log.info("worker started, waiting for orders")

    while _running:
        try:
            item = r.brpop(store.QUEUE_KEY, timeout=2)
        except redis.RedisError as exc:
            log.error("redis error: %s", exc)
            return 1
        if item:
            process(r, catalog, item[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
