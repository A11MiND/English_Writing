from __future__ import annotations

import concurrent.futures
import os
import time
from uuid import uuid4

from http_common import Session


def write_loop(index: int) -> int:
    task_id = os.environ["STRESS_TASK_ID"]
    session = Session()
    session.login(os.getenv("STRESS_STUDENT_EMAIL", "student@wfjosephlee.edu.hk"))
    saves = int(os.getenv("STRESS_AUTOSAVES", "12"))
    ok = 0
    for step in range(saves):
        text = f"Stress writing {index}-{step} {uuid4().hex}"
        status, _ = session.request(
            "PUT",
            f"/api/student/tasks/{task_id}/draft",
            {"content_html": f"<p>{text}</p>", "content_text": text, "word_count": len(text.split())},
        )
        ok += int(status == 200)
    return ok


def main() -> None:
    users = int(os.getenv("STRESS_USERS", "100"))
    workers = int(os.getenv("STRESS_WORKERS", "25"))
    if "STRESS_TASK_ID" not in os.environ:
        raise SystemExit("Set STRESS_TASK_ID to an assigned Practice Mode task.")
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        saves = sum(pool.map(write_loop, range(users)))
    print(
        {
            "scenario": "writing_load",
            "users": users,
            "successful_autosaves": saves,
            "elapsed_seconds": round(time.perf_counter() - started, 2),
        }
    )


if __name__ == "__main__":
    main()
