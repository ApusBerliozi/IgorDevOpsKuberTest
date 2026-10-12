"""Общий доступ к Redis для api и worker."""
import logging
import os

import redis

log = logging.getLogger(__name__)

QUEUE_KEY = "orders:queue"


def order_key(order_id: str) -> str:
    return f"order:{order_id}"


def make_client() -> redis.Redis:
    host = os.environ.get("REDIS_HOST", "localhost")
    port = int(os.environ.get("REDIS_PORT", "6379"))
    password = os.environ.get("REDIS_PASSWORD") or None
    log.info("connecting to redis at %s:%s", host, port)
    return redis.Redis(
        host=host,
        port=port,
        password=password,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=10,
    )
