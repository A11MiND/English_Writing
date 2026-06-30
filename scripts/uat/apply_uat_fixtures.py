from __future__ import annotations

import argparse
import csv
import json
import os
import re
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any


DEFAULT_FIXTURE_DIR = Path("tests/fixtures/uat/minimax")
DEFAULT_PASSWORD = "Password123!"
DEFAULT_TEACHER_EMAIL = "teacher@wfjosephlee.edu.hk"
UAT_RUBRIC_TITLE_TEMPLATE = "UAT {level} School Writing Rubric"


class ApiSession:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, bytes]:
        data = None
        headers = {"accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["content-type"] = "application/json"
        request = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=60)
            return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def login(self, email: str, password: str) -> None:
        status, body = self.request("POST", "/api/auth/login", {"email": email, "password": password})
        if status != 200:
            raise RuntimeError(f"Admin login failed: {status} {body[:300]!r}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_openauth_from_env_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^OPENAUTH_USERS_JSON=(.*)$", text, re.MULTILINE)
    if not match:
        return []
    raw = match.group(1).strip()
    if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
        raw = raw[1:-1]
    return json.loads(raw)


def merge_openauth_users(base_users: list[dict], fixture_users: list[dict]) -> list[dict]:
    merged_by_email = {row["email"].lower(): row for row in base_users}
    for row in fixture_users:
        merged_by_email[row["email"].lower()] = row
    return list(merged_by_email.values())


def import_users(session: ApiSession, role: str, rows: list[dict[str, str]]) -> dict:
    status, body = session.request("POST", "/api/admin/import/users", {"role": role, "rows": rows})
    if status != 200:
        raise RuntimeError(f"Import {role} failed: {status} {body[:300]!r}")
    return json.loads(body.decode("utf-8"))["data"]


def api_data(session: ApiSession, method: str, path: str, payload: dict | None = None) -> dict:
    status, body = session.request(method, path, payload)
    if status >= 400:
        raise RuntimeError(f"{method} {path} failed: {status} {body[:300]!r}")
    decoded = json.loads(body.decode("utf-8"))
    return decoded["data"]


def default_rubric_payload(level: str) -> dict:
    return {
        "title": UAT_RUBRIC_TITLE_TEMPLATE.format(level=level),
        "level": level,
        "total_score": 15,
        "status": "ACTIVE",
        "dimensions": [
            {
                "name": "Content",
                "min_score": 0,
                "max_score": 5,
                "descriptor": "Ideas answer the topic and include relevant, developed details.",
                "sort_order": 1,
            },
            {
                "name": "Language",
                "min_score": 0,
                "max_score": 5,
                "descriptor": "Vocabulary, grammar and sentence patterns are accurate for the level.",
                "sort_order": 2,
            },
            {
                "name": "Organisation",
                "min_score": 0,
                "max_score": 5,
                "descriptor": "Writing has a clear structure, sequence and paragraph flow.",
                "sort_order": 3,
            },
        ],
    }


def normalize_topic(raw_topic: dict[str, Any]) -> dict[str, Any]:
    title = str(raw_topic.get("topic_title") or raw_topic.get("title") or "").strip()
    level = str(raw_topic.get("level") or "").strip().upper()
    mode = str(raw_topic.get("mode") or "").strip().upper()
    if level not in {"P4", "P5", "P6"}:
        raise ValueError(f"Unsupported topic level for {title!r}: {level!r}")
    if mode not in {"PRACTICE", "EXAM"}:
        raise ValueError(f"Unsupported topic mode for {title!r}: {mode!r}")
    word_minimum = raw_topic.get("word_minimum")
    word_maximum = raw_topic.get("word_maximum")
    exam_duration = raw_topic.get("exam_duration_minutes")
    topic = {
        "title": title,
        "level": level,
        "instruction": str(raw_topic.get("instruction") or title).strip(),
        "genre": str(raw_topic.get("genre") or "Writing").strip(),
        "mode": mode,
        "word_minimum": int(word_minimum) if word_minimum is not None else 80,
        "word_maximum": int(word_maximum) if word_maximum is not None else 250,
        "status": "PUBLISHED",
    }
    if mode == "EXAM":
        topic["exam_duration_minutes"] = int(exam_duration or 45)
    return topic


def find_or_create_rubric(session: ApiSession, level: str) -> dict:
    title = UAT_RUBRIC_TITLE_TEMPLATE.format(level=level)
    rubrics = api_data(session, "GET", "/api/teacher/rubrics")["rubrics"]
    for rubric in rubrics:
        if rubric["title"] == title and rubric["level"] == level:
            return rubric
    return api_data(session, "POST", "/api/teacher/rubrics", default_rubric_payload(level))["rubric"]


def existing_task_by_title(session: ApiSession, title: str) -> dict | None:
    tasks = api_data(session, "GET", "/api/teacher/tasks")["tasks"]
    for task in tasks:
        if task["title"] == title:
            return task
    return None


def apply_writing_fixtures(session: ApiSession, fixture_dir: Path) -> dict:
    fixture_path = fixture_dir / "writing-fixtures.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    topics = payload.get("writing_topics")
    if not isinstance(topics, list) or not topics:
        raise RuntimeError(f"{fixture_path} must contain a non-empty writing_topics array.")

    teacher_classes = api_data(session, "GET", "/api/teacher/classes")["classes"]
    classes_by_name = {row["name"].upper(): row for row in teacher_classes}
    rubrics_by_level: dict[str, dict] = {}
    created_tasks: list[dict] = []
    reused_tasks: list[dict] = []
    skipped_topics: list[dict] = []

    for raw_topic in topics:
        topic = normalize_topic(raw_topic)
        class_name = f"{topic['level']}A"
        class_row = classes_by_name.get(class_name)
        if class_row is None:
            skipped_topics.append(
                {
                    "title": topic["title"],
                    "level": topic["level"],
                    "reason": f"Teacher is not assigned to {class_name}.",
                }
            )
            continue

        rubric = rubrics_by_level.setdefault(topic["level"], find_or_create_rubric(session, topic["level"]))
        existing = existing_task_by_title(session, topic["title"])
        if existing is None:
            task_payload = {**topic, "rubric_id": rubric["id"]}
            task = api_data(session, "POST", "/api/teacher/tasks", task_payload)["task"]
            created_tasks.append(task)
        else:
            task = existing
            reused_tasks.append(task)
        assignment = api_data(
            session,
            "POST",
            f"/api/teacher/tasks/{task['id']}/assignments",
            {"class_id": class_row["id"]},
        )["assignment"]
        task["uat_assignment"] = assignment

    result = {
        "source": str(fixture_path),
        "rubric_ids_by_level": {level: rubric["id"] for level, rubric in rubrics_by_level.items()},
        "created_tasks": created_tasks,
        "reused_tasks": reused_tasks,
        "skipped_topics": skipped_topics,
    }
    (fixture_dir / "writing-fixtures.applied.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare and optionally import generated UAT fixtures.")
    parser.add_argument("--fixture-dir", default=str(DEFAULT_FIXTURE_DIR))
    parser.add_argument("--api-base-url", default=os.getenv("UAT_API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--admin-email", default=os.getenv("UAT_ADMIN_EMAIL", "admin@wfjosephlee.edu.hk"))
    parser.add_argument("--admin-password", default=os.getenv("UAT_ADMIN_PASSWORD", DEFAULT_PASSWORD))
    parser.add_argument("--teacher-email", default=os.getenv("UAT_TEACHER_EMAIL", DEFAULT_TEACHER_EMAIL))
    parser.add_argument("--teacher-password", default=os.getenv("UAT_TEACHER_PASSWORD", DEFAULT_PASSWORD))
    parser.add_argument("--base-env", default=".env")
    parser.add_argument("--import-users", action="store_true")
    parser.add_argument("--import-writing-fixtures", action="store_true")
    args = parser.parse_args()

    fixture_dir = Path(args.fixture_dir)
    students = read_csv(fixture_dir / "students.csv")
    teachers = read_csv(fixture_dir / "teachers.csv")
    fixture_openauth = json.loads((fixture_dir / "openauth-users.json").read_text(encoding="utf-8"))
    base_openauth = read_openauth_from_env_file(Path(args.base_env)) if Path(args.base_env).exists() else []
    combined = merge_openauth_users(base_openauth, fixture_openauth)

    (fixture_dir / "openauth-users.combined.json").write_text(
        json.dumps(combined, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (fixture_dir / "openauth-users.combined.env").write_text(
        f"OPENAUTH_USERS_JSON='{json.dumps(combined, separators=(',', ':'), sort_keys=True)}'\n",
        encoding="utf-8",
    )
    write_csv(
        fixture_dir / "stress-student-credentials.csv",
        [
            {"email": row["email"], "password": DEFAULT_PASSWORD, "class_name": row.get("class_name", "")}
            for row in students
        ],
        ["email", "password", "class_name"],
    )

    if args.import_users:
        session = ApiSession(args.api_base_url)
        session.login(args.admin_email, args.admin_password)
        teacher_result = import_users(session, "TEACHER", teachers)
        student_result = import_users(session, "STUDENT", students)
    else:
        teacher_result = {"successful_count": 0, "rejected_count": 0, "dry_run": True}
        student_result = {"successful_count": 0, "rejected_count": 0, "dry_run": True}

    if args.import_writing_fixtures:
        teacher_session = ApiSession(args.api_base_url)
        teacher_session.login(args.teacher_email, args.teacher_password)
        writing_result = apply_writing_fixtures(teacher_session, fixture_dir)
    else:
        writing_result = {"dry_run": True}

    outputs = [
        str(fixture_dir / "openauth-users.combined.json"),
        str(fixture_dir / "openauth-users.combined.env"),
        str(fixture_dir / "stress-student-credentials.csv"),
    ]
    if args.import_writing_fixtures:
        outputs.append(str(fixture_dir / "writing-fixtures.applied.json"))

    print(
        json.dumps(
            {
                "fixture_dir": str(fixture_dir),
                "teachers": len(teachers),
                "students": len(students),
                "combined_openauth_users": len(combined),
                "teacher_import": teacher_result,
                "student_import": student_result,
                "writing_fixture_import": writing_result,
                "outputs": outputs,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
