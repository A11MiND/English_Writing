from __future__ import annotations

import concurrent.futures
import os
import time

from http_common import Session


def login_once(index: int) -> float:
    email = os.getenv("STRESS_LOGIN_EMAIL", "student@wfjosephlee.edu.hk")
    start = time.perf_counter()
    Session().login(email)
    return time.perf_counter() - start


def main() -> None:
    users = int(os.getenv("STRESS_USERS", "150"))
    workers = int(os.getenv("STRESS_WORKERS", "25"))
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        durations = list(pool.map(login_once, range(users)))
    elapsed = time.perf_counter() - started
    print({"scenario": "login_burst", "users": users, "elapsed_seconds": round(elapsed, 2)})
    print({"p95_login_seconds": round(sorted(durations)[int(len(durations) * 0.95) - 1], 3)})


if __name__ == "__main__":
    main()
