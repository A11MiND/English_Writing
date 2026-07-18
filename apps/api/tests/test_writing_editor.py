import asyncio
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.writing import count_words, ensure_submission_allowed
from app.core.database import AsyncSessionLocal
from app.core.responses import ApiException
from app.main import app
from app.models import WritingTask


client = TestClient(app)


def student_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "student@school.example", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def teacher_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "teacher@school.example", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def other_teacher_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "other.teacher@school.example", "password": "Password123!"},
    )
    assert response.status_code == 200
    return session


def admin_session() -> TestClient:
    session = TestClient(app)
    response = session.post(
        "/api/auth/login",
        json={"email": "admin@school.example", "password": "Password123!"},
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
                    "email": "other.teacher@school.example",
                    "display_name": "Other Teacher",
                    "staff_code": "T-OTHER",
                }
            ],
        },
    )
    assert response.status_code == 200


def create_assigned_task(
    mode: str,
    *,
    word_minimum: int = 20,
    word_maximum: int = 80,
    due_at: datetime | None = None,
) -> str:
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
            "word_minimum": word_minimum,
            "word_maximum": word_maximum,
            **({"due_at": due_at.isoformat()} if due_at is not None else {}),
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


def writing_text(word_count: int) -> str:
    return " ".join(f"word{index}" for index in range(word_count))


async def allow_late_submission(task_id: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(WritingTask).where(WritingTask.id == task_id))
        task = result.scalar_one()
        task.allow_late_submission = True
        await db.commit()


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


def test_server_word_count_matches_editor_whitespace_rules() -> None:
    assert count_words("  One short\nstory\twith  spaces. ") == 5
    assert count_words("   ") == 0


def test_submission_constraints_return_specific_error_codes() -> None:
    task = SimpleNamespace(
        due_at=None,
        allow_late_submission=False,
        word_minimum=20,
        word_maximum=80,
    )

    with pytest.raises(ApiException) as below_error:
        ensure_submission_allowed(task, 19)
    assert below_error.value.error_code == "WORD_COUNT_BELOW_MINIMUM"
    assert below_error.value.status_code == 422

    with pytest.raises(ApiException) as above_error:
        ensure_submission_allowed(task, 81)
    assert above_error.value.error_code == "WORD_COUNT_ABOVE_MAXIMUM"
    assert above_error.value.status_code == 422

    task.due_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(ApiException) as deadline_error:
        ensure_submission_allowed(task, 20)
    assert deadline_error.value.error_code == "SUBMISSION_DEADLINE_PASSED"
    assert deadline_error.value.status_code == 409

    task.allow_late_submission = True
    assert ensure_submission_allowed(task, 20) is True


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for writing editor tests.",
)
def test_student_can_autosave_and_submit_practice_task() -> None:
    session = student_session()
    task_id = create_assigned_task("PRACTICE")
    content_text = writing_text(20)

    draft_response = session.put(
        f"/api/student/tasks/{task_id}/draft",
        json={
            "content_html": f"<p>{content_text}</p><script>alert(1)</script>",
            "content_text": content_text,
            "word_count": 1,
        },
    )
    assert draft_response.status_code == 200
    draft = draft_response.json()["data"]["draft"]
    assert "<script>" not in draft["content_html"]
    assert draft["word_count"] == 20

    submit_response = session.post(f"/api/student/tasks/{task_id}/submit", json={})
    assert submit_response.status_code == 200
    submission = submit_response.json()["data"]["submission"]
    assert submission["content_text"] == content_text
    assert submission["word_count"] == 20

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
def test_submit_recalculates_forged_word_count_and_enforces_range() -> None:
    session = student_session()
    task_id = create_assigned_task("PRACTICE")

    below_response = session.post(
        f"/api/student/tasks/{task_id}/submit",
        json={
            "content_html": f"<p>{writing_text(19)}</p>",
            "content_text": writing_text(19),
            "word_count": 80,
        },
    )
    assert below_response.status_code == 422
    assert below_response.json()["error_code"] == "WORD_COUNT_BELOW_MINIMUM"

    above_response = session.post(
        f"/api/student/tasks/{task_id}/submit",
        json={
            "content_html": f"<p>{writing_text(81)}</p>",
            "content_text": writing_text(81),
            "word_count": 20,
        },
    )
    assert above_response.status_code == 422
    assert above_response.json()["error_code"] == "WORD_COUNT_ABOVE_MAXIMUM"

    accepted_text = writing_text(24)
    accepted_response = session.post(
        f"/api/student/tasks/{task_id}/submit",
        json={
            "content_html": f"<p>{accepted_text}</p>",
            "content_text": accepted_text,
            "word_count": 1,
        },
    )
    assert accepted_response.status_code == 200
    assert accepted_response.json()["data"]["submission"]["word_count"] == 24


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for writing editor tests.",
)
def test_deadline_blocks_manual_submit_but_not_autosave_or_allowed_late_submit() -> None:
    session = student_session()
    task_id = create_assigned_task(
        "PRACTICE",
        due_at=datetime.now(UTC) - timedelta(minutes=5),
    )

    draft_response = session.put(
        f"/api/student/tasks/{task_id}/draft",
        json={
            "content_html": "<p>Still drafting</p>",
            "content_text": "Still drafting",
            "word_count": 200,
        },
    )
    assert draft_response.status_code == 200
    assert draft_response.json()["data"]["draft"]["word_count"] == 2

    content_text = writing_text(20)
    blocked_response = session.post(
        f"/api/student/tasks/{task_id}/submit",
        json={
            "content_html": f"<p>{content_text}</p>",
            "content_text": content_text,
            "word_count": 20,
        },
    )
    assert blocked_response.status_code == 409
    assert blocked_response.json()["error_code"] == "SUBMISSION_DEADLINE_PASSED"

    asyncio.run(allow_late_submission(task_id))
    allowed_response = session.post(
        f"/api/student/tasks/{task_id}/submit",
        json={
            "content_html": f"<p>{content_text}</p>",
            "content_text": content_text,
            "word_count": 0,
        },
    )
    assert allowed_response.status_code == 200
    assert allowed_response.json()["data"]["submission"]["word_count"] == 20


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for writing editor tests.",
)
@pytest.mark.parametrize(
    ("actual_word_count", "due_at"),
    [
        (2, None),
        (81, None),
        (2, datetime.now(UTC) - timedelta(minutes=5)),
    ],
)
def test_exam_timer_always_saves_and_locks_writing(
    actual_word_count: int,
    due_at: datetime | None,
) -> None:
    session = student_session()
    task_id = create_assigned_task("EXAM", due_at=due_at)
    content_text = writing_text(actual_word_count)

    submit_response = session.post(
        f"/api/student/tasks/{task_id}/submit",
        json={
            "content_html": f"<p>{content_text}</p>",
            "content_text": content_text,
            "word_count": 20,
            "submission_trigger": "TIMER",
        },
    )
    assert submit_response.status_code == 200
    submission = submit_response.json()["data"]["submission"]
    assert submission["word_count"] == actual_word_count
    assert submit_response.json()["data"]["locked"] is True

    events_response = teacher_session().get(
        f"/api/teacher/submissions/{submission['id']}/exam-events"
    )
    assert events_response.status_code == 200
    event_metadata = events_response.json()["data"]["events"][-1]["metadata"]
    assert event_metadata["source"] == "timer"
    assert event_metadata["constraints_bypassed"] is True
    assert event_metadata["submitted_late"] is (due_at is not None)


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for writing editor tests.",
)
def test_timer_bypass_is_restricted_to_exam_mode() -> None:
    session = student_session()
    practice_task_id = create_assigned_task("PRACTICE")
    exam_task_id = create_assigned_task("EXAM")
    short_text = writing_text(2)

    practice_timer_response = session.post(
        f"/api/student/tasks/{practice_task_id}/submit",
        json={
            "content_html": f"<p>{writing_text(20)}</p>",
            "content_text": writing_text(20),
            "word_count": 20,
            "submission_trigger": "TIMER",
        },
    )
    assert practice_timer_response.status_code == 422
    assert practice_timer_response.json()["error_code"] == "SUBMISSION_TRIGGER_NOT_ALLOWED"

    exam_manual_response = session.post(
        f"/api/student/tasks/{exam_task_id}/submit",
        json={
            "content_html": f"<p>{short_text}</p>",
            "content_text": short_text,
            "word_count": 20,
        },
    )
    assert exam_manual_response.status_code == 422
    assert exam_manual_response.json()["error_code"] == "WORD_COUNT_BELOW_MINIMUM"


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

    content_text = writing_text(20)
    submit_response = student.post(
        f"/api/student/tasks/{exam_task_id}/submit",
        json={
            "content_html": f"<p>{content_text}</p>",
            "content_text": content_text,
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
