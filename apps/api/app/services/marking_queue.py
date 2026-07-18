from __future__ import annotations

from typing import Any, Protocol

from redis.asyncio import Redis
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.core.config import Settings, get_settings


class AsyncRedisQueueClient(Protocol):
    async def rpush(self, key: str, value: str) -> int:
        ...

    async def blpop(self, keys: str | list[str], timeout: int = 0) -> Any:
        ...

    async def llen(self, key: str) -> int:
        ...

    async def aclose(self) -> None:
        ...


def create_redis_client(settings: Settings | None = None) -> Redis:
    settings = settings or get_settings()
    return Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)


async def enqueue_marking_job(
    marking_result_id: str,
    *,
    redis_client: AsyncRedisQueueClient | None = None,
    settings: Settings | None = None,
) -> int:
    settings = settings or get_settings()
    owns_client = redis_client is None
    client = redis_client or create_redis_client(settings)
    try:
        return await client.rpush(settings.marking_queue_name, marking_result_id)
    finally:
        if owns_client:
            await client.aclose()


async def dequeue_marking_job(
    *,
    redis_client: AsyncRedisQueueClient | None = None,
    settings: Settings | None = None,
    timeout_seconds: int | None = None,
) -> str | None:
    settings = settings or get_settings()
    owns_client = redis_client is None
    client = redis_client or create_redis_client(settings)
    timeout = settings.marking_worker_poll_timeout_seconds if timeout_seconds is None else timeout_seconds
    try:
        try:
            result = await client.blpop(settings.marking_queue_name, timeout=timeout)
        except RedisTimeoutError:
            result = None
    finally:
        if owns_client:
            await client.aclose()
    if not result:
        return None
    _, value = result
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


async def pending_marking_job_count(
    *,
    redis_client: AsyncRedisQueueClient | None = None,
    settings: Settings | None = None,
) -> int:
    settings = settings or get_settings()
    owns_client = redis_client is None
    client = redis_client or create_redis_client(settings)
    try:
        return await client.llen(settings.marking_queue_name)
    finally:
        if owns_client:
            await client.aclose()
