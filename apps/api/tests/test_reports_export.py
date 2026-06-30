import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.reports import sanitize_csv_cell


client = TestClient(app)


def teacher_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "teacher@wfjosephlee.edu.hk", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def student_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "student@wfjosephlee.edu.hk", "password": "Password123!"},
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


def p5a_class_id(session: TestClient) -> str:
    response = session.get("/api/teacher/classes")
    assert response.status_code == 200
    for row in response.json()["data"]["classes"]:
        if row["name"] == "P5A":
            return row["id"]
    raise AssertionError("P5A was not seeded")


def create_report_task(session: TestClient, class_id: str) -> str:
    rubric_response = session.get("/api/teacher/rubrics")
    assert rubric_response.status_code == 200
    rubric_id = rubric_response.json()["data"]["rubrics"][0]["id"]
    suffix = uuid4().hex[:8]
    task_response = session.post(
        "/api/teacher/tasks",
        json={
            "title": f"Report Task {suffix}",
            "level": "P5",
            "instruction": "Write a short paragraph for report export tests.",
            "genre": "Narrative",
            "mode": "PRACTICE",
            "word_minimum": 20,
            "word_maximum": 80,
            "rubric_id": rubric_id,
            "status": "PUBLISHED",
        },
    )
    assert task_response.status_code == 200
    task_id = task_response.json()["data"]["task"]["id"]
    assign_response = session.post(
        f"/api/teacher/tasks/{task_id}/assignments",
        json={"class_id": class_id},
    )
    assert assign_response.status_code == 200
    return task_id


def test_report_endpoint_rejects_unauthenticated_request() -> None:
    response = client.get("/api/teacher/reports/classes/11111111-1111-4111-8111-111111111111")

    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_REQUIRED"


def test_csv_export_sanitizes_formula_cells() -> None:
    assert sanitize_csv_cell("=IMPORTXML(\"http://example.test\")") == "'=IMPORTXML(\"http://example.test\")"
    assert sanitize_csv_cell("+cmd") == "'+cmd"
    assert sanitize_csv_cell("-1+2") == "'-1+2"
    assert sanitize_csv_cell("@SUM(A1:A2)") == "'@SUM(A1:A2)"
    assert sanitize_csv_cell("normal text") == "normal text"
    assert sanitize_csv_cell(12) == 12


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for report/export tests.",
)
def test_teacher_generates_report_and_exports_csv_pdf() -> None:
    teacher = teacher_session()
    class_id = p5a_class_id(teacher)
    task_id = create_report_task(teacher, class_id)

    student = student_session()
    submit_response = student.post(
        f"/api/student/tasks/{task_id}/submit",
        json={
            "content_html": "<p>I helped a classmate finish a difficult exercise.</p>",
            "content_text": "I helped a classmate finish a difficult exercise.",
            "word_count": 8,
        },
    )
    assert submit_response.status_code == 200

    report_response = teacher.post(
        f"/api/teacher/reports/classes/{class_id}/generate?task_id={task_id}"
    )
    assert report_response.status_code == 200
    report = report_response.json()["data"]
    assert report["class_report"]["id"]
    assert report["summary"]["student_count"] >= 1
    assert report["summary"]["submitted_count"] >= 1
    assert any(row["submitted"] for row in report["completion_rows"])

    csv_response = teacher.get(f"/api/teacher/reports/classes/{class_id}/export.csv?task_id={task_id}")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "student_number,student_name,task_title" in csv_response.text

    pdf_response = teacher.get(f"/api/teacher/reports/classes/{class_id}/export.pdf?task_id={task_id}")
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")

    audit_response = teacher.get(f"/api/teacher/reports/classes/{class_id}/exports")
    assert audit_response.status_code == 200
    exports = audit_response.json()["data"]["exports"]
    assert any(row["format"] == "csv" and row["task_id"] == task_id for row in exports)
    assert any(row["format"] == "pdf" and row["task_id"] == task_id for row in exports)


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for report/export tests.",
)
def test_teacher_cannot_report_unassigned_class() -> None:
    admin = admin_session()
    suffix = uuid4().hex[:6]
    class_response = admin.post(
        "/api/admin/classes",
        json={"name": f"P6X{suffix}", "level": "P6", "academic_year": "2026-2027"},
    )
    assert class_response.status_code == 200
    unassigned_class_id = class_response.json()["data"]["class"]["id"]

    response = teacher_session().get(f"/api/teacher/reports/classes/{unassigned_class_id}")

    assert response.status_code == 403
    assert response.json()["error_code"] == "ACCESS_DENIED"

    audit_response = teacher_session().get(f"/api/teacher/reports/classes/{unassigned_class_id}/exports")
    assert audit_response.status_code == 403
    assert audit_response.json()["error_code"] == "ACCESS_DENIED"
