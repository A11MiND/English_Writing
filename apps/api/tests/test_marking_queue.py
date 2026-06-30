from __future__ import annotations

import pytest

from app.core.config import Settings
from app.services.marking_queue import (
    dequeue_marking_job,
    enqueue_marking_job,
    pending_marking_job_count,
)


class FakeRedisQueue:
    def __init__(self) -> None:
        self.values: list[tuple[str, str]] = []
        self.closed = False

    async def rpush(self, key: str, value: str) -> int:
        self.values.append((key, value))
        return len(self.values)

    async def blpop(self, keys: str | list[str], timeout: int = 0):
        key = keys[0] if isinstance(keys, list) else keys
        for index, (stored_key, value) in enumerate(self.values):
            if stored_key == key:
                self.values.pop(index)
                return stored_key, value
        return None

    async def llen(self, key: str) -> int:
        return len([value for stored_key, value in self.values if stored_key == key])

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_marking_queue_enqueue_dequeue_and_count() -> None:
    redis = FakeRedisQueue()
    settings = Settings(marking_queue_name="test:marking")

    queue_depth = await enqueue_marking_job("marking-1", redis_client=redis, settings=settings)
    pending = await pending_marking_job_count(redis_client=redis, settings=settings)
    dequeued = await dequeue_marking_job(redis_client=redis, settings=settings, timeout_seconds=1)

    assert queue_depth == 1
    assert pending == 1
    assert dequeued == "marking-1"
    assert await pending_marking_job_count(redis_client=redis, settings=settings) == 0
    assert redis.closed is False
