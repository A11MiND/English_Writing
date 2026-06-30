import os
import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models import MarkingResult


client = TestClient(app)


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


def student_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "student@wfjosephlee.edu.hk", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def other_student_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "other.student@wfjosephlee.edu.hk", "password": "Password123!"},
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


def ensure_other_student_imported() -> None:
    response = admin_session().post(
        "/api/admin/import/users",
        json={
            "role": "STUDENT",
            "rows": [
                {
                    "external_user_id": "55555555-5555-4555-8555-555555555556",
                    "email": "other.student@wfjosephlee.edu.hk",
                    "display_name": "Other Student",
                    "student_number": "S0998",
                    "level": "P5",
                    "class_name": "P5A",
                }
            ],
        },
    )
    assert response.status_code == 200


def ensure_other_teacher_imported() -> None:
    response = admin_session().post(
        "/api/admin/import/users",
        json={
            "role": "TEACHER",
            "rows": [
                {
                    "external_user_id": "44444444-4444-4444-8444-444444444445",
                    "email": "other.teacher@wfjosephlee.edu.hk",
                    "display_name": "Other Teacher",
                    "staff_code": "T0998",
                }
            ],
        },
    )
    assert response.status_code == 200


def create_assigned_task() -> str:
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
            "title": f"AI Marking Task {suffix}",
            "level": "P5",
            "instruction": "Write a short story for the marking test.",
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
    assign_response = teacher.post(
        f"/api/teacher/tasks/{task_id}/assignments",
        json={"class_id": class_id},
    )
    assert assign_response.status_code == 200
    return task_id


def p5a_class_id(session: TestClient) -> str:
    response = session.get("/api/teacher/classes")
    assert response.status_code == 200
    for row in response.json()["data"]["classes"]:
        if row["name"] == "P5A":
            return row["id"]
    raise AssertionError("P5A was not seeded")


def submit_writing_and_get_marking_result() -> tuple[TestClient, str, str]:
    task_id = create_assigned_task()
    student = student_session()
    submit_response = student.post(
        f"/api/student/tasks/{task_id}/submit",
        json={
            "content_html": "<p>I helped my friend at school yesterday.</p>",
            "content_text": "I helped my friend at school yesterday.",
            "word_count": 7,
        },
    )
    assert submit_response.status_code == 200
    submission_id = submit_response.json()["data"]["submission"]["id"]

    teacher = teacher_session()
    list_response = teacher.get("/api/teacher/marking/submissions")
    assert list_response.status_code == 200
    item = next(
        row
        for row in list_response.json()["data"]["items"]
        if row["submission"]["id"] == submission_id
    )
    return teacher, item["marking_result"]["id"], submission_id


async def mark_result_as_ai_marked(marking_result_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MarkingResult).where(MarkingResult.id == marking_result_id))
        row = result.scalar_one()
        row.status = "AI_MARKED"
        row.content_score = 4
        row.language_score = 4
        row.organisation_score = 4
        row.total_score = 12
        row.confidence_level = "HIGH"
        row.content_feedback = "The writing answers the topic with relevant ideas."
        row.language_feedback = "The language is mostly clear."
        row.organisation_feedback = "The writing has a clear sequence."
        row.strengths = ["Relevant ideas"]
        row.weaknesses = ["Add more details"]
        row.sentence_level_comments = []
        row.recommended_exercises = [
            {
                "title": "Add supporting details",
                "exercise_type": "revision",
                "focus_area": "Content",
                "prompt": "Rewrite one sentence with one extra supporting detail.",
            }
        ]
        row.warning_flags = []
        row.model_metadata = {"test_setup": "permission_boundary"}
        await db.commit()


def test_teacher_marking_endpoint_rejects_unauthenticated_request() -> None:
    response = client.get("/api/teacher/marking/submissions")

    assert response.status_code == 401
    assert response.json()["error_code"] == "AUTH_REQUIRED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for marking workflow tests.",
)
def test_teacher_review_rejects_invalid_score_payloads() -> None:
    teacher, marking_result_id, _ = submit_writing_and_get_marking_result()

    over_max_response = teacher.post(
        f"/api/teacher/marking-results/{marking_result_id}/review",
        json={
            "content_score": 6,
            "language_score": 4,
            "organisation_score": 4,
            "total_score": 14,
            "status": "REVIEWED",
        },
    )
    assert over_max_response.status_code == 422

    mismatch_response = teacher.post(
        f"/api/teacher/marking-results/{marking_result_id}/review",
        json={
            "content_score": 5,
            "language_score": 4,
            "organisation_score": 4,
            "total_score": 15,
            "status": "REVIEWED",
        },
    )
    assert mismatch_response.status_code == 422

    bypass_release_response = teacher.post(
        f"/api/teacher/marking-results/{marking_result_id}/review",
        json={
            "content_score": 5,
            "language_score": 4,
            "organisation_score": 4,
            "total_score": 13,
            "status": "RELEASED",
        },
    )
    assert bypass_release_response.status_code == 422


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for marking workflow tests.",
)
def test_released_feedback_and_exercises_are_scoped_to_owner_student() -> None:
    ensure_other_student_imported()
    teacher, marking_result_id, submission_id = submit_writing_and_get_marking_result()
    asyncio.run(mark_result_as_ai_marked(marking_result_id))

    release_response = teacher.post(f"/api/teacher/marking-results/{marking_result_id}/release")
    assert release_response.status_code == 200

    owner = student_session()
    feedback_response = owner.get(f"/api/student/submissions/{submission_id}/feedback")
    assert feedback_response.status_code == 200
    exercises = feedback_response.json()["data"]["exercises"]
    assert exercises

    other = other_student_session()
    other_feedback_response = other.get(f"/api/student/submissions/{submission_id}/feedback")
    assert other_feedback_response.status_code == 404
    assert other_feedback_response.json()["error_code"] == "NOT_FOUND"

    other_exercise_response = other.post(
        f"/api/student/exercises/{exercises[0]['id']}/complete",
        json={"response_text": "Trying to complete another student's exercise."},
    )
    assert other_exercise_response.status_code == 404
    assert other_exercise_response.json()["error_code"] == "NOT_FOUND"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for marking workflow tests.",
)
def test_teacher_cannot_mark_review_or_release_unassigned_class_submission() -> None:
    ensure_other_teacher_imported()
    assigned_teacher, marking_result_id, submission_id = submit_writing_and_get_marking_result()
    assert assigned_teacher.get("/api/teacher/marking/submissions").status_code == 200

    other_teacher = other_teacher_session()
    list_response = other_teacher.get("/api/teacher/marking/submissions")
    assert list_response.status_code == 200
    visible_submission_ids = {
        item["submission"]["id"] for item in list_response.json()["data"]["items"]
    }
    assert submission_id not in visible_submission_ids

    run_response = other_teacher.post(f"/api/teacher/marking-results/{marking_result_id}/run")
    assert run_response.status_code == 404
    assert run_response.json()["error_code"] == "NOT_FOUND"

    review_response = other_teacher.post(
        f"/api/teacher/marking-results/{marking_result_id}/review",
        json={
            "content_score": 4,
            "language_score": 4,
            "organisation_score": 4,
            "total_score": 12,
            "status": "REVIEWED",
        },
    )
    assert review_response.status_code == 404
    assert review_response.json()["error_code"] == "NOT_FOUND"

    release_response = other_teacher.post(f"/api/teacher/marking-results/{marking_result_id}/release")
    assert release_response.status_code == 404
    assert release_response.json()["error_code"] == "NOT_FOUND"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for marking workflow tests.",
)
def test_teacher_marking_list_filters_and_dashboard_summary() -> None:
    teacher, marking_result_id, submission_id = submit_writing_and_get_marking_result()
    class_id = p5a_class_id(teacher)
    all_response = teacher.get("/api/teacher/marking/submissions")
    assert all_response.status_code == 200
    item = next(
        row for row in all_response.json()["data"]["items"] if row["submission"]["id"] == submission_id
    )
    task_id = item["task"]["id"]

    class_filter_response = teacher.get(f"/api/teacher/marking/submissions?class_id={class_id}")
    assert class_filter_response.status_code == 200
    assert any(
        row["submission"]["id"] == submission_id
        for row in class_filter_response.json()["data"]["items"]
    )

    task_filter_response = teacher.get(f"/api/teacher/marking/submissions?task_id={task_id}")
    assert task_filter_response.status_code == 200
    assert [row["task"]["id"] for row in task_filter_response.json()["data"]["items"]].count(task_id) >= 1

    status_filter_response = teacher.get("/api/teacher/marking/submissions?status=QUEUED")
    assert status_filter_response.status_code == 200
    filtered_item = next(
        row
        for row in status_filter_response.json()["data"]["items"]
        if row["marking_result"]["id"] == marking_result_id
    )
    assert filtered_item["marking_result"]["status"] == "QUEUED"

    summary_response = teacher.get(f"/api/teacher/dashboard-summary?class_id={class_id}&task_id={task_id}")
    assert summary_response.status_code == 200
    summary = summary_response.json()["data"]["summary"]
    assert summary["assigned_class_count"] >= 1
    assert summary["active_task_count"] >= 1
    assert summary["submitted_count"] >= 1
    assert summary["pending_marking_count"] >= 1
    assert summary["marking_status_counts"]["QUEUED"] >= 1


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1" or os.getenv("RUN_LLM_TESTS") != "1" or not os.getenv("LLM_API_KEY"),
    reason="Set RUN_DB_TESTS=1, RUN_LLM_TESTS=1 and a real LLM_API_KEY for marking workflow tests.",
)
def test_submission_creates_marking_job_and_teacher_can_mark_and_review() -> None:
    task_id = create_assigned_task()
    student = student_session()
    submit_response = student.post(
        f"/api/student/tasks/{task_id}/submit",
        json={
            "content_html": "<p>I helped my friend at school yesterday.</p>",
            "content_text": "I helped my friend at school yesterday.",
            "word_count": 7,
        },
    )
    assert submit_response.status_code == 200
    submission_id = submit_response.json()["data"]["submission"]["id"]

    teacher = teacher_session()
    list_response = teacher.get("/api/teacher/marking/submissions")
    assert list_response.status_code == 200
    item = next(
        row
        for row in list_response.json()["data"]["items"]
        if row["submission"]["id"] == submission_id
    )
    marking_result = item["marking_result"]
    assert marking_result["status"] in {"QUEUED", "AI_MARKED"}

    run_response = teacher.post(f"/api/teacher/marking-results/{marking_result['id']}/run")
    assert run_response.status_code == 200
    marked = run_response.json()["data"]["marking_result"]
    assert marked["status"] == "AI_MARKED"
    assert marked["total_score"] is not None

    unreleased_feedback_response = student.get(f"/api/student/submissions/{submission_id}/feedback")
    assert unreleased_feedback_response.status_code == 404

    review_response = teacher.post(
        f"/api/teacher/marking-results/{marking_result['id']}/review",
        json={
            "content_score": 5,
            "language_score": 4,
            "organisation_score": 4,
            "total_score": 13,
            "review_notes": "Teacher adjusted content score after review.",
            "status": "REVIEWED",
        },
    )
    assert review_response.status_code == 200
    review = review_response.json()["data"]["review"]
    assert review["total_score"] == 13
    assert review["status"] == "REVIEWED"

    release_response = teacher.post(f"/api/teacher/marking-results/{marking_result['id']}/release")
    assert release_response.status_code == 200
    assert release_response.json()["data"]["review"]["status"] == "RELEASED"

    feedback_response = student.get(f"/api/student/submissions/{submission_id}/feedback")
    assert feedback_response.status_code == 200
    feedback = feedback_response.json()["data"]
    assert feedback["review"]["status"] == "RELEASED"
    assert feedback["review"]["total_score"] == 13
    assert len(feedback["exercises"]) >= 1

    exercise_id = feedback["exercises"][0]["id"]
    complete_response = student.post(
        f"/api/student/exercises/{exercise_id}/complete",
        json={"response_text": "I revised the paragraph with clearer linking words."},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["data"]["exercise"]["status"] == "COMPLETED"
