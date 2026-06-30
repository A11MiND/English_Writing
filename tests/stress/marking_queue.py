from __future__ import annotations

import concurrent.futures
import os
import time

from http_common import Session


def trigger_marking(marking_result_id: str) -> int:
    session = Session()
    session.login(os.getenv("STRESS_TEACHER_EMAIL", "teacher@wfjosephlee.edu.hk"))
    status, _ = session.request("POST", f"/api/teacher/marking-results/{marking_result_id}/run")
    return int(status == 200)


def main() -> None:
    ids = [item.strip() for item in os.environ["STRESS_MARKING_RESULT_IDS"].split(",") if item.strip()]
    workers = int(os.getenv("STRESS_WORKERS", "20"))
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        completed = sum(pool.map(trigger_marking, ids))
    print(
        {
            "scenario": "marking_queue",
            "marking_jobs": len(ids),
            "triggered": completed,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
        }
    )


if __name__ == "__main__":
    main()
