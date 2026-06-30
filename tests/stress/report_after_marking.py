from __future__ import annotations

import os

from http_common import Session


def main() -> None:
    class_id = os.environ["STRESS_CLASS_ID"]
    session = Session()
    session.login(os.getenv("STRESS_TEACHER_EMAIL", "teacher@wfjosephlee.edu.hk"))
    status, body = session.request("POST", f"/api/teacher/reports/classes/{class_id}/generate")
    if status != 200:
        raise SystemExit(f"Report generation failed: {status} {body[:200]!r}")
    csv_status, csv_body = session.request("GET", f"/api/teacher/reports/classes/{class_id}/export.csv")
    if csv_status != 200:
        raise SystemExit(f"CSV export failed: {csv_status} {csv_body[:200]!r}")
    print({"scenario": "report_after_marking", "class_id": class_id, "csv_bytes": len(csv_body)})


if __name__ == "__main__":
    main()
