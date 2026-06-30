from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from uuid import uuid4


BASE_URL = os.getenv("LIVE_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
PASSWORD = os.getenv("LIVE_PASSWORD", "Password123!")
TEACHER_EMAIL = os.getenv("LIVE_TEACHER_EMAIL", "teacher@wfjosephlee.edu.hk")
STUDENT_EMAIL = os.getenv("LIVE_STUDENT_EMAIL", "student@wfjosephlee.edu.hk")


def request(opener: urllib.request.OpenerDirector, method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"content-type": "application/json"} if payload is not None else {},
        method=method,
    )
    try:
        with opener.open(req, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed with HTTP {exc.code}: {body}") from exc


def login(email: str) -> urllib.request.OpenerDirector:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    body = request(opener, "POST", "/api/auth/login", {"email": email, "password": PASSWORD})
    if not body.get("success"):
        raise RuntimeError(f"Login failed for {email}")
    return opener


def main() -> int:
    teacher = login(TEACHER_EMAIL)
    student = login(STUDENT_EMAIL)

    rubrics = request(teacher, "GET", "/api/teacher/rubrics")["data"]["rubrics"]
    classes = request(teacher, "GET", "/api/teacher/classes")["data"]["classes"]
    rubric_id = rubrics[0]["id"]
    class_id = next(row["id"] for row in classes if row["name"] == "P5A")

    suffix = uuid4().hex[:8]
    task = request(
        teacher,
        "POST",
        "/api/teacher/tasks",
        {
            "title": f"Live DeepSeek Smoke {suffix}",
            "level": "P5",
            "instruction": "Write a short story about helping a friend at school.",
            "genre": "Narrative",
            "mode": "PRACTICE",
            "word_minimum": 20,
            "word_maximum": 120,
            "rubric_id": rubric_id,
            "status": "PUBLISHED",
        },
    )["data"]["task"]
    request(teacher, "POST", f"/api/teacher/tasks/{task['id']}/assignments", {"class_id": class_id})

    submission = request(
        student,
        "POST",
        f"/api/student/tasks/{task['id']}/submit",
        {
            "content_html": "<p>Yesterday I helped my friend when he could not finish his homework. I explained the question and we solved it together.</p>",
            "content_text": "Yesterday I helped my friend when he could not finish his homework. I explained the question and we solved it together.",
            "word_count": 20,
        },
    )["data"]["submission"]

    marking_items = request(teacher, "GET", "/api/teacher/marking/submissions")["data"]["items"]
    marking = next(row["marking_result"] for row in marking_items if row["submission"]["id"] == submission["id"])
    marked = request(teacher, "POST", f"/api/teacher/marking-results/{marking['id']}/run")["data"]["marking_result"]

    print(
        json.dumps(
            {
                "submission_id": submission["id"],
                "marking_result_id": marked["id"],
                "status": marked["status"],
                "total_score": marked["total_score"],
                "attempts": marked["attempts"],
                "model_metadata_keys": sorted(marked["model_metadata"].keys()),
            },
            indent=2,
        )
    )
    return 0 if marked["status"] == "AI_MARKED" else 1


if __name__ == "__main__":
    sys.exit(main())
