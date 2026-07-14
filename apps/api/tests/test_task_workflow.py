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
        json={"email": "teacher@wfjosephlee.edu.hk", "password": "Password123!"},
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


def student_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "student@wfjosephlee.edu.hk", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def rubric_payload(title: str, level: str = "P5") -> dict:
    return {
        "title": title,
        "level": level,
        "total_score": 15,
        "status": "ACTIVE",
        "dimensions": [
            {
                "name": "Content",
                "min_score": 0,
                "max_score": 5,
                "descriptor": "Ideas are relevant and developed.",
                "sort_order": 1,
            },
            {
                "name": "Language",
                "min_score": 0,
                "max_score": 5,
                "descriptor": "Vocabulary and grammar are accurate.",
                "sort_order": 2,
            },
            {
                "name": "Organisation",
                "min_score": 0,
                "max_score": 5,
                "descriptor": "Writing is logically sequenced.",
                "sort_order": 3,
            },
        ],
    }


def create_rubric(session: TestClient) -> str:
    suffix = uuid4().hex[:8]
    response = session.post("/api/teacher/rubrics", json=rubric_payload(f"Test Rubric {suffix}"))
    assert response.status_code == 200
    return response.json()["data"]["rubric"]["id"]


def create_task(session: TestClient, rubric_id: str, status: str = "PUBLISHED") -> str:
    suffix = uuid4().hex[:8]
    response = session.post(
        "/api/teacher/tasks",
        json={
            "title": f"Test Task {suffix}",
            "level": "P5",
            "instruction": "Write a story with a clear beginning, middle and ending.",
            "genre": "Narrative",
            "mode": "PRACTICE",
            "word_minimum": 120,
            "word_maximum": 180,
            "rubric_id": rubric_id,
            "status": status,
        },
    )
    assert response.status_code == 200
    return response.json()["data"]["task"]["id"]


def p5a_class_id(session: TestClient) -> str:
    response = session.get("/api/teacher/classes")
    assert response.status_code == 200
    for row in response.json()["data"]["classes"]:
        if row["name"] == "P5A":
            return row["id"]
    raise AssertionError("P5A was not seeded")


def test_teacher_task_endpoint_rejects_unauthenticated_request() -> None:
    response = client.get("/api/teacher/tasks")

    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_REQUIRED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for task workflow tests.",
)
def test_teacher_creates_rubric_with_required_dimensions() -> None:
    session = teacher_session()

    response = session.post("/api/teacher/rubrics", json=rubric_payload("Phase 3 Rubric"))

    assert response.status_code == 200
    rubric = response.json()["data"]["rubric"]
    assert rubric["title"] == "Phase 3 Rubric"
    assert [dimension["name"] for dimension in rubric["dimensions"]] == [
        "Content",
        "Language",
        "Organisation",
    ]


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for task workflow tests.",
)
def test_teacher_creates_task_and_assigns_to_class() -> None:
    session = teacher_session()
    rubric_id = create_rubric(session)
    task_id = create_task(session, rubric_id)
    class_id = p5a_class_id(session)

    response = session.post(f"/api/teacher/tasks/{task_id}/assignments", json={"class_id": class_id})

    assert response.status_code == 200
    assert response.json()["data"]["assignment"]["class_name"] == "P5A"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for task workflow tests.",
)
def test_teacher_rubrics_include_usage_count_and_task_detail_includes_assignments() -> None:
    session = teacher_session()
    rubric_id = create_rubric(session)
    task_id = create_task(session, rubric_id)
    class_id = p5a_class_id(session)
    assign_response = session.post(f"/api/teacher/tasks/{task_id}/assignments", json={"class_id": class_id})
    assert assign_response.status_code == 200

    rubrics_response = session.get("/api/teacher/rubrics")
    assert rubrics_response.status_code == 200
    rubric = next(row for row in rubrics_response.json()["data"]["rubrics"] if row["id"] == rubric_id)
    assert rubric["used_by_task_count"] == 1

    task_response = session.get(f"/api/teacher/tasks/{task_id}")
    assert task_response.status_code == 200
    task = task_response.json()["data"]["task"]
    assert task["id"] == task_id
    assert task["rubric_id"] == rubric_id
    assert task["assigned_classes"] == ["P5A"]


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for task workflow tests.",
)
def test_exam_task_requires_and_returns_duration() -> None:
    session = teacher_session()
    rubric_id = create_rubric(session)
    payload = {
        "title": f"Exam Duration {uuid4().hex[:8]}",
        "level": "P5",
        "instruction": "Write under timed exam conditions.",
        "genre": "Narrative",
        "mode": "EXAM",
        "word_minimum": 120,
        "word_maximum": 180,
        "rubric_id": rubric_id,
        "status": "PUBLISHED",
    }

    rejected = session.post("/api/teacher/tasks", json=payload)
    assert rejected.status_code == 422

    accepted = session.post("/api/teacher/tasks", json={**payload, "exam_duration_minutes": 45})
    assert accepted.status_code == 200
    task = accepted.json()["data"]["task"]
    assert task["mode"] == "EXAM"
    assert task["exam_duration_minutes"] == 45


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for task workflow tests.",
)
def test_student_sees_only_published_assigned_tasks() -> None:
    teacher = teacher_session()
    rubric_id = create_rubric(teacher)
    published_task_id = create_task(teacher, rubric_id, "PUBLISHED")
    draft_task_id = create_task(teacher, rubric_id, "DRAFT")
    class_id = p5a_class_id(teacher)
    teacher.post(f"/api/teacher/tasks/{published_task_id}/assignments", json={"class_id": class_id})
    teacher.post(f"/api/teacher/tasks/{draft_task_id}/assignments", json={"class_id": class_id})

    response = student_session().get("/api/student/tasks")

    assert response.status_code == 200
    task_ids = [row["id"] for row in response.json()["data"]["tasks"]]
    assert published_task_id in task_ids
    assert draft_task_id not in task_ids


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for task workflow tests.",
)
def test_student_task_list_includes_draft_submission_and_feedback_state() -> None:
    teacher = teacher_session()
    rubric_id = create_rubric(teacher)
    task_id = create_task(teacher, rubric_id, "PUBLISHED")
    class_id = p5a_class_id(teacher)
    teacher.post(f"/api/teacher/tasks/{task_id}/assignments", json={"class_id": class_id})

    student = student_session()
    draft_text = " ".join(f"word{index}" for index in range(120))
    draft_response = student.put(
        f"/api/student/tasks/{task_id}/draft",
        json={
            "content_html": f"<p>{draft_text}</p>",
            "content_text": draft_text,
            "word_count": 120,
        },
    )
    assert draft_response.status_code == 200

    draft_list_response = student.get("/api/student/tasks")
    assert draft_list_response.status_code == 200
    draft_task = next(row for row in draft_list_response.json()["data"]["tasks"] if row["id"] == task_id)
    assert draft_task["draft_status"] == "ACTIVE"
    assert draft_task["submission_id"] is None
    assert draft_task["locked"] is False
    assert draft_task["feedback_released"] is False

    submit_response = student.post(f"/api/student/tasks/{task_id}/submit", json={})
    assert submit_response.status_code == 200
    submission_id = submit_response.json()["data"]["submission"]["id"]

    submitted_list_response = student.get("/api/student/tasks")
    assert submitted_list_response.status_code == 200
    submitted_task = next(
        row for row in submitted_list_response.json()["data"]["tasks"] if row["id"] == task_id
    )
    assert submitted_task["draft_status"] == "SUBMITTED"
    assert submitted_task["submission_id"] == submission_id
    assert submitted_task["submission_status"] == "SUBMITTED"
    assert submitted_task["locked"] is True
    assert submitted_task["feedback_released"] is False


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for task workflow tests.",
)
def test_teacher_cannot_assign_task_to_unassigned_class() -> None:
    admin = admin_session()
    suffix = uuid4().hex[:6]
    class_response = admin.post(
        "/api/admin/classes",
        json={"name": f"P4X{suffix}", "level": "P4", "academic_year": "2026-2027"},
    )
    assert class_response.status_code == 200
    unassigned_class_id = class_response.json()["data"]["class"]["id"]

    teacher = teacher_session()
    rubric_id = create_rubric(teacher)
    task_id = create_task(teacher, rubric_id)

    response = teacher.post(
        f"/api/teacher/tasks/{task_id}/assignments",
        json={"class_id": unassigned_class_id},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "ACCESS_DENIED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for task workflow tests.",
)
def test_teacher_duplicates_and_archives_used_rubric_instead_of_editing_scores() -> None:
    teacher = teacher_session()
    rubric_id = create_rubric(teacher)
    create_task(teacher, rubric_id)

    edit_response = teacher.patch(
        f"/api/teacher/rubrics/{rubric_id}",
        json={
            "title": "Changed Used Rubric",
            "level": "P5",
            "total_score": 15,
            "dimensions": rubric_payload("Changed Used Rubric")["dimensions"],
        },
    )
    assert edit_response.status_code == 422
    assert edit_response.json()["error_code"] == "VALIDATION_ERROR"

    duplicate_response = teacher.post(
        f"/api/teacher/rubrics/{rubric_id}/duplicate",
        json={"title": "Editable Rubric Copy"},
    )
    assert duplicate_response.status_code == 200
    duplicate = duplicate_response.json()["data"]["rubric"]
    assert duplicate["title"] == "Editable Rubric Copy"
    assert duplicate["status"] == "DRAFT"
    assert [dimension["name"] for dimension in duplicate["dimensions"]] == [
        "Content",
        "Language",
        "Organisation",
    ]

    archive_response = teacher.patch(
        f"/api/teacher/rubrics/{rubric_id}",
        json={"status": "ARCHIVED"},
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["data"]["rubric"]["status"] == "ARCHIVED"

    list_response = teacher.get("/api/teacher/rubrics")
    assert list_response.status_code == 200
    rubric_ids = [row["id"] for row in list_response.json()["data"]["rubrics"]]
    assert rubric_id not in rubric_ids
    assert duplicate["id"] in rubric_ids


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for task workflow tests.",
)
def test_teacher_updates_task_status_lifecycle() -> None:
    teacher = teacher_session()
    rubric_id = create_rubric(teacher)
    task_id = create_task(teacher, rubric_id, "DRAFT")

    publish_response = teacher.patch(f"/api/teacher/tasks/{task_id}", json={"status": "PUBLISHED"})
    assert publish_response.status_code == 200
    assert publish_response.json()["data"]["task"]["status"] == "PUBLISHED"

    close_response = teacher.patch(f"/api/teacher/tasks/{task_id}", json={"status": "CLOSED"})
    assert close_response.status_code == 200
    assert close_response.json()["data"]["task"]["status"] == "CLOSED"

    archive_response = teacher.patch(f"/api/teacher/tasks/{task_id}", json={"status": "ARCHIVED"})
    assert archive_response.status_code == 200
    assert archive_response.json()["data"]["task"]["status"] == "ARCHIVED"
