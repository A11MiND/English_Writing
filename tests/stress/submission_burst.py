from __future__ import annotations

import concurrent.futures
import os
import time
from uuid import uuid4

from http_common import Session


def submit_once(index: int) -> int:
    task_id = os.environ["STRESS_TASK_ID"]
    session = Session()
    session.login(os.getenv("STRESS_STUDENT_EMAIL", "student@wfjosephlee.edu.hk"))
    text = f"Stress submission {index} {uuid4().hex}"
    status, _ = session.request(
        "POST",
        f"/api/student/tasks/{task_id}/submit",
        {"content_html": f"<p>{text}</p>", "content_text": text, "word_count": len(text.split())},
    )
    return int(status == 200 or status == 409)


def main() -> None:
    users = int(os.getenv("STRESS_USERS", "470"))
    workers = int(os.getenv("STRESS_WORKERS", "40"))
    if "STRESS_TASK_ID" not in os.environ:
        raise SystemExit("Set STRESS_TASK_ID to an assigned task.")
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        accepted = sum(pool.map(submit_once, range(users)))
    print(
        {
            "scenario": "submission_burst",
            "users": users,
            "accepted_or_locked": accepted,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
        }
    )


if __name__ == "__main__":
    main()
