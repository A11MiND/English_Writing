import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def teacher_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "teacher@school.example", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def student_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "student@school.example", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


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
            "title": f"Suggestion Task {mode} {suffix}",
            "level": "P5",
            "instruction": "Write a paragraph for suggestion testing.",
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


def test_suggestions_endpoint_rejects_unauthenticated_request() -> None:
    response = client.post(
        "/api/suggestions/check",
        json={"task_id": "dddddddd-dddd-4ddd-8ddd-dddddddddd01", "text": "teh mistake"},
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_REQUIRED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for suggestion tests.",
)
def test_practice_mode_suggestions_return_normalized_spans_and_exam_rejects() -> None:
    student = student_session()
    practice_task_id = create_assigned_task("PRACTICE")
    exam_task_id = create_assigned_task("EXAM")

    response = student.post(
        "/api/suggestions/check",
        json={"task_id": practice_task_id, "text": "i dont like teh  error.", "check_mode": "FULL"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["service_status"] == "ok"
    assert body["check_mode"] == "FULL"
    assert len(body["suggestions"]) >= 1
    assert all(row["offset"] >= 0 and row["length"] >= 1 for row in body["suggestions"])
    assert all(isinstance(row["replacements"], list) for row in body["suggestions"])
    assert all(row["level"] in {"WORD", "SENTENCE"} for row in body["suggestions"])

    denied = student.post(
        "/api/suggestions/check",
        json={"task_id": exam_task_id, "text": "teh error"},
    )
    assert denied.status_code == 403
    assert denied.json()["error_code"] == "ACCESS_DENIED"
