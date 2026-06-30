import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def student_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "student@wfjosephlee.edu.hk", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def teacher_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "teacher@wfjosephlee.edu.hk", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def other_teacher_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "other.teacher@wfjosephlee.edu.hk", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def admin_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "admin@wfjosephlee.edu.hk", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def ensure_other_teacher_imported() -> None:
    admin = admin_session()
    response = admin.post(
        "/api/admin/import/users",
        json={
            "role": "TEACHER",
            "rows": [
                {
                    "email": "other.teacher@wfjosephlee.edu.hk",
                    "display_name": "Other Teacher",
                    "staff_code": "T-OTHER",
                }
            ],
        },
    )
    assert response.status_code == 200


def create_assigned_task(mode: str) -> str:
    teacher = teacher_session()
    rubrics_response = teacher.get("/api/teacher/rubrics")
    assert rubrics_response.status_code == 200
    rubric_id = rubrics_response.json()["data"]["rubrics"][0]["id"]

    classes_response = teacher.get("/api/teacher/classes")
    assert classes_response.status_code == 200
    class_id = next(
        row["id"] for row in classes_response.json()["data"]["classes"] if row["name"] == "P5A"
    )
    suffix = uuid4().hex[:8]
    task_response = teacher.post(
        "/api/teacher/tasks",
        json={
            "title": f"Writing Editor {mode} {suffix}",
            "level": "P5",
            "instruction": "Write a short story for the editor test.",
            "genre": "Narrative",
            "mode": mode,
            "word_minimum": 20,
            "word_maximum": 80,
            **({"exam_duration_minutes": 30} if mode == "EXAM" else {}),
            "rubric_id": rubric_id,
            "status": "PUBLISHED",
        },
    )
    assert task_response.status_code == 200
    task_id = task_response.json()["data"]["task"]["id"]
    assign_response = teacher.post(
        f"/api/teacher/tasks/{task_id}/assignments",
        json={"class_id": class_id},
    )
    assert assign_response.status_code == 200
    return task_id


def seeded_task_id(session: TestClient, mode: str) -> str:
    response = session.get("/api/student/tasks")
    assert response.status_code == 200
    for task in response.json()["data"]["tasks"]:
        if task["mode"] == mode and task["id"].startswith("dddddddd"):
            return task["id"]
    raise AssertionError(f"No seeded {mode} task found")


def test_writing_workspace_rejects_unauthenticated_request() -> None:
    response = client.get("/api/student/tasks/dddddddd-dddd-4ddd-8ddd-dddddddddd01/writing")

    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_REQUIRED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for writing editor tests.",
)
def test_student_can_autosave_and_submit_practice_task() -> None:
    session = student_session()
    task_id = create_assigned_task("PRACTICE")

    draft_response = session.put(
        f"/api/student/tasks/{task_id}/draft",
        json={
            "content_html": "<p>Hello <script>alert(1)</script>world</p>",
            "content_text": "Hello world",
            "word_count": 2,
        },
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]["draft"]
    assert "<script>" not in draft["content_html"]
    assert draft["word_count"] == 2

    submit_response = session.post(f"/api/student/tasks/{task_id}/submit", json={})
    assert submit_response.status_code == 200
    submission = submit_response.json()["data"]["submission"]
    assert submission["content_text"] == "Hello world"

    locked_response = session.put(
        f"/api/student/tasks/{task_id}/draft",
        json={"content_html": "<p>Changed</p>", "content_text": "Changed", "word_count": 1},
    )
    assert locked_response.status_code == 409
    assert locked_response.json()["error_code"] == "SUBMISSION_LOCKED"

    second_submit_response = session.post(
        f"/api/student/tasks/{task_id}/submit",
        json={"content_html": "<p>Changed</p>", "content_text": "Changed", "word_count": 1},
    )
    assert second_submit_response.status_code == 409
    assert second_submit_response.json()["error_code"] == "SUBMISSION_LOCKED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for writing editor tests.",
)
def test_exam_events_are_recorded_for_exam_task_only() -> None:
    session = student_session()
    exam_task_id = create_assigned_task("EXAM")
    practice_task_id = create_assigned_task("PRACTICE")

    event_response = session.post(
        f"/api/student/tasks/{exam_task_id}/exam-events",
        json={"event_type": "PASTE_ATTEMPT", "metadata": {"source": "test"}},
    )
    assert event_response.status_code == 200
    assert event_response.json()["data"]["event"]["event_type"] == "PASTE_ATTEMPT"

    denied_response = session.post(
        f"/api/student/tasks/{practice_task_id}/exam-events",
        json={"event_type": "PASTE_ATTEMPT", "metadata": {"source": "test"}},
    )
    assert denied_response.status_code == 403
    assert denied_response.json()["error_code"] == "ACCESS_DENIED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for writing editor tests.",
)
def test_teacher_can_review_exam_events_for_assigned_submission_only() -> None:
    ensure_other_teacher_imported()
    student = student_session()
    exam_task_id = create_assigned_task("EXAM")

    paste_response = student.post(
        f"/api/student/tasks/{exam_task_id}/exam-events",
        json={"event_type": "PASTE_ATTEMPT", "metadata": {"source": "test"}},
    )
    assert paste_response.status_code == 200

    submit_response = student.post(
        f"/api/student/tasks/{exam_task_id}/submit",
        json={
            "content_html": "<p>Timed writing answer</p>",
            "content_text": "Timed writing answer",
            "word_count": 3,
        },
    )
    assert submit_response.status_code == 200
    submission_id = submit_response.json()["data"]["submission"]["id"]

    teacher_response = teacher_session().get(f"/api/teacher/submissions/{submission_id}/exam-events")
    assert teacher_response.status_code == 200
    payload = teacher_response.json()["data"]
    assert payload["submission_id"] == submission_id
    assert payload["task_id"] == exam_task_id
    assert payload["mode"] == "EXAM"
    assert payload["class_name"] == "P5A"
    assert [event["event_type"] for event in payload["events"]] == ["PASTE_ATTEMPT", "SUBMISSION"]
    assert payload["events"][0]["metadata"] == {"source": "test"}

    other_teacher_response = other_teacher_session().get(
        f"/api/teacher/submissions/{submission_id}/exam-events"
    )
    assert other_teacher_response.status_code == 404
    assert other_teacher_response.json()["error_code"] == "NOT_FOUND"
