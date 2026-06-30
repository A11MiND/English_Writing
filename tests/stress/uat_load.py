from __future__ import annotations

import concurrent.futures
import csv
import json
import os
import statistics
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from http_common import Session


TEACHER_EMAIL = os.getenv("STRESS_TEACHER_EMAIL", "teacher@wfjosephlee.edu.hk")
STUDENT_EMAIL = os.getenv("STRESS_STUDENT_EMAIL", "student@wfjosephlee.edu.hk")
EVIDENCE_DIR = Path(os.getenv("STRESS_EVIDENCE_DIR", "docs/uat-evidence/2026-06-29"))


@dataclass(frozen=True)
class Credential:
    email: str
    password: str
    class_name: str | None = None


def now_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


class EvidenceWriter:
    def __init__(self) -> None:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        self.path = EVIDENCE_DIR / f"stress-{now_id()}.jsonl"

    def write(self, payload: dict) -> None:
        payload = {"recorded_at": datetime.now(UTC).isoformat(), **payload}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        print(payload)


def api_json(session: Session, method: str, path: str, payload: dict | None = None) -> dict:
    status, body = session.request(method, path, payload)
    if status >= 400:
        raise RuntimeError(f"{method} {path} failed: {status} {body[:300]!r}")
    return json.loads(body.decode("utf-8"))["data"]


def teacher_session() -> Session:
    session = Session()
    session.login(TEACHER_EMAIL)
    return session


def student_session() -> Session:
    session = Session()
    session.login(STUDENT_EMAIL)
    return session


def credential_session(credential: Credential | None = None) -> Session:
    session = Session()
    if credential is None:
        session.login(STUDENT_EMAIL)
    else:
        session.login(credential.email, credential.password)
    return session


def load_student_credentials() -> list[Credential]:
    csv_path = os.getenv("STRESS_STUDENT_CREDENTIALS_CSV")
    if not csv_path:
        return []
    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        Credential(
            email=row["email"],
            password=row.get("password") or os.getenv("STRESS_PASSWORD", "Password123!"),
            class_name=(row.get("class_name") or None),
        )
        for row in rows
        if row.get("email")
    ]


def pick_credentials(credentials: list[Credential], count: int) -> list[Credential | None]:
    if not credentials:
        return [None] * count
    if len(credentials) < count:
        raise RuntimeError(f"Need {count} credentials but only found {len(credentials)}.")
    return list(credentials[:count])


def first_rubric_id(session: Session) -> str:
    data = api_json(session, "GET", "/api/teacher/rubrics")
    return data["rubrics"][0]["id"]


def p5a_class_id(session: Session) -> str:
    data = api_json(session, "GET", "/api/teacher/classes")
    for row in data["classes"]:
        if row["name"] == "P5A":
            return row["id"]
    raise RuntimeError("P5A class not found")


def teacher_classes_by_name(session: Session) -> dict[str, dict]:
    data = api_json(session, "GET", "/api/teacher/classes")
    return {row["name"]: row for row in data["classes"]}


def create_task(
    session: Session,
    rubric_id: str,
    class_id: str,
    title: str,
    mode: str = "PRACTICE",
    level: str = "P5",
) -> str:
    payload = {
        "title": title,
        "level": level,
        "instruction": "Stress-test writing task for controlled pilot load evidence.",
        "genre": "Narrative",
        "mode": mode,
        "word_minimum": 20,
        "word_maximum": 120,
        "rubric_id": rubric_id,
        "status": "PUBLISHED",
    }
    if mode == "EXAM":
        payload["exam_duration_minutes"] = 30
    task = api_json(session, "POST", "/api/teacher/tasks", payload)["task"]
    api_json(session, "POST", f"/api/teacher/tasks/{task['id']}/assignments", {"class_id": class_id})
    return task["id"]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * pct) - 1))
    return round(ordered[index], 3)


def run_login_burst(evidence: EvidenceWriter, credentials: list[Credential]) -> None:
    users = int(os.getenv("STRESS_LOGIN_USERS", "150"))
    workers = int(os.getenv("STRESS_LOGIN_WORKERS", "25"))
    selected = pick_credentials(credentials, users)

    def login_once(credential: Credential | None) -> float:
        started = time.perf_counter()
        credential_session(credential)
        return time.perf_counter() - started

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        durations = list(pool.map(login_once, selected))
    elapsed = time.perf_counter() - started
    evidence.write(
        {
            "scenario": "150_students_login_within_10_minutes",
            "credential_strategy": "distinct_student_accounts" if credentials else "shared_seed_student_account",
            "target_users": users,
            "workers": workers,
            "elapsed_seconds": round(elapsed, 2),
            "p50_login_seconds": percentile(durations, 0.50),
            "p95_login_seconds": percentile(durations, 0.95),
            "passed": elapsed <= 600,
        }
    )


def task_for_credential(
    credential: Credential | None,
    default_task_id: str,
    task_ids_by_class_name: dict[str, str] | None = None,
) -> str:
    if credential and credential.class_name and task_ids_by_class_name:
        return task_ids_by_class_name.get(credential.class_name, default_task_id)
    return default_task_id


def run_writing_load(
    evidence: EvidenceWriter,
    task_id: str,
    credentials: list[Credential],
    task_ids_by_class_name: dict[str, str] | None = None,
) -> None:
    users = int(os.getenv("STRESS_WRITING_USERS", "100"))
    workers = int(os.getenv("STRESS_WRITING_WORKERS", "25"))
    autosaves = int(os.getenv("STRESS_AUTOSAVES", "3"))
    selected = pick_credentials(credentials, users)

    def write_once(item: tuple[int, Credential | None]) -> tuple[int, int, float]:
        index, credential = item
        assigned_task_id = task_for_credential(credential, task_id, task_ids_by_class_name)
        session = credential_session(credential)
        ok_saves = 0
        ok_suggestions = 0
        started = time.perf_counter()
        for step in range(autosaves):
            text = f"Stress writing {index}-{step} teh sentence {uuid4().hex}"
            status, _ = session.request(
                "PUT",
                f"/api/student/tasks/{assigned_task_id}/draft",
                {"content_html": f"<p>{text}</p>", "content_text": text, "word_count": len(text.split())},
            )
            ok_saves += int(status == 200)
        status, _ = session.request(
            "POST",
            "/api/suggestions/check",
            {"task_id": assigned_task_id, "text": f"Stress suggestion teh error {index}", "check_mode": "FULL"},
        )
        ok_suggestions += int(status == 200)
        return ok_saves, ok_suggestions, time.perf_counter() - started

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(write_once, enumerate(selected)))
    elapsed = time.perf_counter() - started
    durations = [row[2] for row in results]
    evidence.write(
        {
            "scenario": "100_concurrent_students_writing_autosave_and_suggestions",
            "credential_strategy": "distinct_student_accounts" if credentials else "shared_seed_student_account",
            "target_users": users,
            "workers": workers,
            "autosaves_per_user": autosaves,
            "successful_autosaves": sum(row[0] for row in results),
            "successful_suggestion_checks": sum(row[1] for row in results),
            "elapsed_seconds": round(elapsed, 2),
            "p95_user_loop_seconds": percentile(durations, 0.95),
            "passed": sum(row[0] for row in results) == users * autosaves and sum(row[1] for row in results) == users,
        }
    )


def create_submission_tasks(count: int, rubric_id: str, class_id: str) -> list[str]:
    session = teacher_session()
    prefix = f"Stress Submission {now_id()}"
    return [
        create_task(session, rubric_id, class_id, f"{prefix} #{index:03d}", "PRACTICE")
        for index in range(count)
    ]


def create_distinct_class_tasks(
    session: Session,
    rubric_id: str,
    classes_by_name: dict[str, dict],
    prefix: str,
    mode: str = "PRACTICE",
) -> dict[str, str]:
    task_ids: dict[str, str] = {}
    for class_name, class_row in classes_by_name.items():
        if class_name not in {"P4A", "P5A", "P6A"}:
            continue
        level = class_row.get("level") or class_name[:2]
        task_ids[class_name] = create_task(
            session,
            rubric_id,
            class_row["id"],
            f"{prefix} {class_name}",
            mode,
            level=level,
        )
    return task_ids


def run_submission_burst(
    evidence: EvidenceWriter,
    task_ids: list[str],
    credentials: list[Credential],
    shared_task_id: str | None = None,
    task_ids_by_class_name: dict[str, str] | None = None,
) -> list[str]:
    users = len(credentials) if credentials else len(task_ids)
    workers = int(os.getenv("STRESS_SUBMISSION_WORKERS", "40"))
    selected = pick_credentials(credentials, users)

    def submit_once(item: tuple[int, Credential | None]) -> tuple[int, str | None, float]:
        index, credential = item
        task_id = task_for_credential(credential, shared_task_id or task_ids[index], task_ids_by_class_name)
        session = credential_session(credential)
        text = f"Stress submission {index} {uuid4().hex}"
        started = time.perf_counter()
        status, body = session.request(
            "POST",
            f"/api/student/tasks/{task_id}/submit",
            {"content_html": f"<p>{text}</p>", "content_text": text, "word_count": len(text.split())},
        )
        marking_result_id = None
        if status == 200:
            payload = json.loads(body.decode("utf-8"))["data"]
            marking_result_id = payload["marking_job"]["id"]
        return int(status == 200), marking_result_id, time.perf_counter() - started

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(submit_once, enumerate(selected)))
    elapsed = time.perf_counter() - started
    durations = [row[2] for row in results]
    marking_ids = [row[1] for row in results if row[1]]
    evidence.write(
        {
            "scenario": "470_submissions_within_30_minutes",
            "credential_strategy": (
                "distinct_student_accounts_single_task"
                if credentials
                else "shared_seed_student_across_unique_tasks"
            ),
            "target_submissions": users,
            "workers": workers,
            "successful_submissions": sum(row[0] for row in results),
            "queued_marking_jobs": len(marking_ids),
            "elapsed_seconds": round(elapsed, 2),
            "p95_submission_seconds": percentile(durations, 0.95),
            "passed": elapsed <= 1800 and sum(row[0] for row in results) == users,
        }
    )
    evidence.write(
        {
            "scenario": "470_essays_queued_for_marking",
            "queued_marking_jobs": len(marking_ids),
            "worker_drain": "not_run_in_this_stress_pass",
            "passed": len(marking_ids) == users,
        }
    )
    return marking_ids


def run_report_after_marking(evidence: EvidenceWriter, class_id: str) -> None:
    session = teacher_session()
    started = time.perf_counter()
    report = api_json(session, "POST", f"/api/teacher/reports/classes/{class_id}/generate")
    csv_status, csv_body = session.request("GET", f"/api/teacher/reports/classes/{class_id}/export.csv")
    elapsed = time.perf_counter() - started
    evidence.write(
        {
            "scenario": "teacher_generates_report_after_marking_queue",
            "class_id": class_id,
            "student_count": report["summary"]["student_count"],
            "expected_submissions": report["summary"]["expected_submissions"],
            "submitted_count": report["summary"]["submitted_count"],
            "csv_status": csv_status,
            "csv_bytes": len(csv_body),
            "elapsed_seconds": round(elapsed, 2),
            "passed": csv_status == 200,
        }
    )


def main() -> None:
    evidence = EvidenceWriter()
    credentials = load_student_credentials()
    teacher = teacher_session()
    rubric_id = first_rubric_id(teacher)
    classes_by_name = teacher_classes_by_name(teacher)
    class_id = classes_by_name.get("P5A", next(iter(classes_by_name.values())))["id"]
    if credentials:
        writing_task_ids_by_class = create_distinct_class_tasks(
            teacher,
            rubric_id,
            classes_by_name,
            f"Stress Writing {now_id()}",
            "PRACTICE",
        )
        writing_task_id = writing_task_ids_by_class.get("P5A") or next(iter(writing_task_ids_by_class.values()))
    else:
        writing_task_ids_by_class = None
        writing_task_id = create_task(teacher, rubric_id, class_id, f"Stress Writing {now_id()}", "PRACTICE")

    submission_count = int(os.getenv("STRESS_SUBMISSION_USERS", "470"))
    evidence.write(
        {
            "scenario": "stress_setup",
            "rubric_id": rubric_id,
            "class_id": class_id,
            "writing_task_id": writing_task_id,
            "writing_task_ids_by_class": writing_task_ids_by_class or {},
            "submission_task_count": submission_count,
        }
    )
    run_login_burst(evidence, credentials)
    run_writing_load(evidence, writing_task_id, credentials, writing_task_ids_by_class)
    if credentials:
        submission_task_ids_by_class = create_distinct_class_tasks(
            teacher_session(),
            rubric_id,
            classes_by_name,
            f"Stress Distinct Student Submission {now_id()}",
            "PRACTICE",
        )
        submission_task_id = submission_task_ids_by_class.get("P5A") or next(iter(submission_task_ids_by_class.values()))
        task_ids = [submission_task_id] * min(submission_count, len(credentials))
        marking_ids = run_submission_burst(
            evidence,
            task_ids,
            credentials[:submission_count],
            shared_task_id=submission_task_id,
            task_ids_by_class_name=submission_task_ids_by_class,
        )
    else:
        task_ids = create_submission_tasks(submission_count, rubric_id, class_id)
        marking_ids = run_submission_burst(evidence, task_ids, credentials)
    run_report_after_marking(evidence, class_id)

    summary = {
        "scenario": "stress_summary",
            "evidence_file": str(evidence.path),
            "distinct_student_credentials": len(credentials),
            "marking_result_ids_sample": marking_ids[:10],
        "marking_result_ids_total": len(marking_ids),
        "limitations": [
            "Uses distinct generated student credentials when STRESS_STUDENT_CREDENTIALS_CSV is set; otherwise falls back to the seeded student credential.",
            "Marking worker drain is intentionally not triggered here to avoid hundreds of paid live LLM calls.",
        ],
    }
    evidence.write(summary)


if __name__ == "__main__":
    main()
