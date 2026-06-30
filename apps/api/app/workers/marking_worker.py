from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import MarkingResult
from app.services.marking import process_marking_result
from app.services.marking_queue import dequeue_marking_job

logger = logging.getLogger("marking_worker")


async def process_one_marking_job(timeout_seconds: int = 5) -> bool:
    marking_result_id = await dequeue_marking_job(timeout_seconds=timeout_seconds)
    if marking_result_id is None:
        return False

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MarkingResult).where(MarkingResult.id == marking_result_id))
        marking_result = result.scalar_one_or_none()
        if marking_result is None:
            logger.warning("Skipping missing marking result %s", marking_result_id)
            return True
        if marking_result.status != "QUEUED":
            logger.info(
                "Skipping marking result %s with status %s",
                marking_result.id,
                marking_result.status,
            )
            return True

        await process_marking_result(db, marking_result)
        await db.commit()
        logger.info("Processed marking result %s with status %s", marking_result.id, marking_result.status)
        return True


async def run_forever() -> None:
    logger.info("Starting marking worker")
    while True:
        try:
            await process_one_marking_job()
        except Exception:
            logger.exception("Marking worker loop failed")
            await asyncio.sleep(2)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
