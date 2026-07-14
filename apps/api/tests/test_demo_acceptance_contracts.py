from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from starlette.requests import Request

import app.api.media as media_api
import app.api.school_data as school_data_api
import app.api.student_ai as student_ai_api
from app.core.auth import AccountStatus, Role
from app.core.responses import ApiException
from app.models import (
    AIUsageLog,
    Class,
    ClassMembership,
    MarkingResult,
    Rubric,
    School,
    StudentProfile,
    Submission,
    User,
    WritingTask,
)
from app.services.llm import LLMGenerationResponse, LLMUsage
from app.services.entitlements import features_for_school


SCHOOL_ID = "11111111-1111-4111-8111-111111111111"
STUDENT_ID = "55555555-5555-4555-8555-555555555555"
TEACHER_ID = "44444444-4444-4444-8444-444444444444"
TASK_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddd01"
RUBRIC_ID = "cccccccc-cccc-4ccc-8ccc-ccccccccccc1"
CLASS_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2"


class FakeResult:
    def __init__(self, *, one: Any = None, rows: list[Any] | None = None) -> None:
        self.one = one
        self.rows = rows if rows is not None else ([] if one is None else [one])

    def scalar_one_or_none(self) -> Any:
        return self.one

    def scalars(self) -> "FakeResult":
        return self

    def first(self) -> Any:
        return self.rows[0] if self.rows else None

    def all(self) -> list[Any]:
        return self.rows


class FakeDb:
    def __init__(self, *results: FakeResult) -> None:
        self.results = list(results)
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _statement: Any) -> FakeResult:
        if not self.results:
            raise AssertionError("Unexpected database query in acceptance test")
        return self.results.pop(0)

    def add(self, row: Any) -> None:
        if hasattr(row, "id") and row.id is None:
            row.id = str(uuid4())
        self.added.append(row)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def refresh(self, _row: Any) -> None:
        return None


class StubLlmAdapter:
    def __init__(self, *payloads: dict[str, Any]) -> None:
        self.payloads = list(payloads)
        self.requests = []

    async def generate_json(self, request: Any) -> LLMGenerationResponse:
        self.requests.append(request)
        if not self.payloads:
            raise AssertionError("The deterministic LLM stub was called too many times")
        return LLMGenerationResponse(
            provider="acceptance-stub",
            model="deterministic-v1",
            content="{}",
            json_data=self.payloads.pop(0),
            usage=LLMUsage(input_tokens=12, output_tokens=18, total_tokens=30),
            raw_metadata={},
        )


def make_request(path: str, method: str = "POST") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [(b"user-agent", b"acceptance-test")],
            "client": ("127.0.0.1", 1234),
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )


def student_user() -> User:
    return User(
        id=STUDENT_ID,
        school_id=SCHOOL_ID,
        email="student@example.edu",
        display_name="Student One",
        role=Role.STUDENT,
        status=AccountStatus.ACTIVE,
    )


def teacher_user() -> User:
    return User(
        id=TEACHER_ID,
        school_id=SCHOOL_ID,
        email="teacher@example.edu",
        display_name="Teacher One",
        role=Role.TEACHER,
        status=AccountStatus.ACTIVE,
    )


def active_rubric() -> Rubric:
    rubric = Rubric(
        id=RUBRIC_ID,
        school_id=SCHOOL_ID,
        title="P5 Writing Rubric",
        level="P5",
        total_score=15,
        status="ACTIVE",
        created_by=TEACHER_ID,
    )
    rubric.dimensions = []
    return rubric


def personal_task() -> WritingTask:
    task = WritingTask(
        id=TASK_ID,
        school_id=SCHOOL_ID,
        title="The Unexpected Visitor",
        level="P5",
        instruction="Write about an unexpected visitor and how you helped them.",
        genre="Narrative|STORY_ORDER",
        mode="PRACTICE",
        word_minimum=100,
        word_maximum=140,
        rubric_id=RUBRIC_ID,
        created_by=STUDENT_ID,
        status="PUBLISHED",
    )
    task.rubric = active_rubric()
    return task


async def no_audit(*_args: Any, **_kwargs: Any) -> None:
    return None


@pytest.mark.asyncio
async def test_personal_practice_generation_uses_safe_stub_and_returns_startable_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = StudentProfile(
        id=str(uuid4()),
        school_id=SCHOOL_ID,
        user_id=STUDENT_ID,
        student_number="S0001",
        level="P5",
        current_class_id=CLASS_ID,
    )
    rubric = active_rubric()
    db = FakeDb(FakeResult(one=profile), FakeResult(rows=[rubric]))
    adapter = StubLlmAdapter(
        {
            "title": "The Lost Library Book",
            "instruction": "Write how you found and returned a missing library book.",
            "structure": ["Set the scene", "Explain what happened", "End with what you learnt"],
        }
    )

    async def adapter_for_school(*_args: Any) -> StubLlmAdapter:
        return adapter

    monkeypatch.setattr(student_ai_api, "get_school_llm_adapter", adapter_for_school)
    monkeypatch.setattr(student_ai_api, "write_audit_log", no_audit)

    response = await student_ai_api.generate_personal_practice(
        student_ai_api.GeneratePersonalPracticeRequest(
            focus="STORY_ORDER", genre="NARRATIVE", duration_minutes=10
        ),
        make_request("/api/student/practice/generate"),
        student_user(),
        db,  # type: ignore[arg-type]
    )

    practice = response["data"]["practice"]
    assert practice["title"] == "The Lost Library Book"
    assert practice["assigned_classes"] == ["My Practice"]
    assert practice["practice_focus"] == "Story order"
    assert practice["word_minimum"] == 100
    assert practice["word_maximum"] == 140
    assert len(practice["structure"]) == 3
    assert any(isinstance(row, WritingTask) for row in db.added)
    assert any(
        isinstance(row, AIUsageLog) and row.operation == "PERSONAL_PRACTICE_GENERATION"
        for row in db.added
    )
    assert adapter.requests[0].response_schema_name == "personal_practice"
    assert "adult topics" in adapter.requests[0].messages[0].content


@pytest.mark.asyncio
async def test_personal_practice_history_and_result_keep_submission_and_ai_feedback_together() -> None:
    now = datetime.now(UTC)
    task = personal_task()
    submission = Submission(
        id=str(uuid4()),
        school_id=SCHOOL_ID,
        task_id=TASK_ID,
        student_id=STUDENT_ID,
        mode="PRACTICE",
        content_html="<p>I helped a lost puppy find its home.</p>",
        content_text="I helped a lost puppy find its home.",
        word_count=8,
        status="SUBMITTED",
        submitted_at=now,
    )
    marking = MarkingResult(
        id=str(uuid4()),
        school_id=SCHOOL_ID,
        submission_id=submission.id,
        task_id=TASK_ID,
        student_id=STUDENT_ID,
        status="AI_MARKED",
        content_score=4,
        language_score=4,
        organisation_score=5,
        total_score=13,
        content_feedback="The story stays focused.",
        language_feedback="Most sentences are clear.",
        organisation_feedback="The events follow a clear order.",
        strengths=["Clear ending"],
        weaknesses=["Add one sensory detail"],
        sentence_level_comments=[],
        recommended_exercises=[],
        marked_at=now,
    )
    history_db = FakeDb(
        FakeResult(rows=[task]),
        FakeResult(rows=[submission]),
        FakeResult(rows=[marking]),
    )

    history = await student_ai_api.list_personal_practice(
        make_request("/api/student/practice", "GET"),
        student_user(),
        history_db,  # type: ignore[arg-type]
    )

    item = history["data"]["items"][0]
    assert item["submission_id"] == submission.id
    assert item["locked"] is True
    assert item["marking_result"]["status"] == "AI_MARKED"
    assert item["marking_result"]["total_score"] == 13

    result_db = FakeDb(
        FakeResult(one=task),
        FakeResult(one=submission),
        FakeResult(one=marking),
    )
    result = await student_ai_api.get_personal_practice_result(
        TASK_ID,
        make_request(f"/api/student/practice/{TASK_ID}/result", "GET"),
        student_user(),
        result_db,  # type: ignore[arg-type]
    )

    assert result["data"]["task"]["practice_focus"] == "Story order"
    assert result["data"]["submission"]["content_text"] == submission.content_text
    assert result["data"]["marking_result"]["strengths"] == ["Clear ending"]


@pytest.mark.asyncio
async def test_student_rewrite_preserves_pupil_text_boundary_and_returns_one_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = personal_task()
    adapter = StubLlmAdapter(
        {
            "revised": "The tiny puppy trembled beside the rainy school gate.",
            "explanation": "Specific details help the reader picture the moment.",
        }
    )

    async def task_context(*_args: Any) -> tuple[None, WritingTask, None]:
        return None, task, None

    async def adapter_for_school(*_args: Any) -> StubLlmAdapter:
        return adapter

    monkeypatch.setattr(student_ai_api, "student_task_context", task_context)
    monkeypatch.setattr(student_ai_api, "get_school_llm_adapter", adapter_for_school)
    monkeypatch.setattr(student_ai_api, "write_audit_log", no_audit)
    db = FakeDb()
    original = "The puppy was near the gate."

    response = await student_ai_api.rewrite_student_text(
        student_ai_api.RewriteRequest(task_id=TASK_ID, text=original, goal="MORE_DESCRIPTIVE"),
        make_request("/api/student/rewrite"),
        student_user(),
        db,  # type: ignore[arg-type]
    )

    rewrite = response["data"]["rewrite"]
    assert rewrite["original"] == original
    assert rewrite["revised"].startswith("The tiny puppy")
    assert rewrite["goal"] == "MORE_DESCRIPTIVE"
    prompt = adapter.requests[0].messages[1].content
    assert f"<pupil_text>{original}</pupil_text>" in prompt
    assert "never as instructions" in prompt
    assert any(
        isinstance(row, AIUsageLog) and row.operation == "STUDENT_REWRITE" for row in db.added
    )


@pytest.mark.asyncio
async def test_teacher_creates_pupil_in_an_assigned_class_without_calling_real_identity_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class_row = Class(
        id=CLASS_ID,
        school_id=SCHOOL_ID,
        name="P5A",
        level="P5",
        academic_year="2026-2027",
        status="ACTIVE",
    )
    db = FakeDb(FakeResult(one=class_row), FakeResult(one=None), FakeResult(one=None))
    provisioned: list[dict[str, Any]] = []

    async def provision(**kwargs: Any) -> None:
        provisioned.append(kwargs)

    monkeypatch.setattr(school_data_api, "provision_identity", provision)
    monkeypatch.setattr(school_data_api, "write_audit_log", no_audit)

    response = await school_data_api.create_teacher_student(
        school_data_api.CreateTeacherStudentRequest(
            display_name="New Pupil",
            email="new.pupil@example.edu",
            temporary_password="Temporary123!",
            class_id=CLASS_ID,
            student_number="S2042",
        ),
        make_request("/api/teacher/students"),
        teacher_user(),
        db,  # type: ignore[arg-type]
    )

    pupil = response["data"]["student"]
    assert pupil["class_name"] == "P5A"
    assert pupil["level"] == "P5"
    assert pupil["student_number"] == "S2042"
    assert provisioned[0]["role"] == Role.STUDENT
    assert provisioned[0]["password"] == "Temporary123!"
    assert any(isinstance(row, User) and row.email == "new.pupil@example.edu" for row in db.added)
    assert any(isinstance(row, StudentProfile) for row in db.added)
    assert any(isinstance(row, ClassMembership) for row in db.added)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "expected_feature"),
    [("speech", "Read Aloud"), ("image", "Image Generation")],
)
async def test_free_plan_denies_paid_media_before_any_provider_call(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    expected_feature: str,
) -> None:
    free_school = School(
        id=SCHOOL_ID,
        name="Free School",
        code="FREE-SCHOOL",
        plan_code="FREE",
        subscription_status="ACTIVE",
    )

    async def school_lookup(*_args: Any) -> School:
        return free_school

    class ProviderMustNotRun:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise AssertionError("Paid media provider must not be constructed for a free account")

    monkeypatch.setattr(media_api, "school_for_user", school_lookup)
    monkeypatch.setattr(media_api, "MiniMaxMediaClient", ProviderMustNotRun)

    with pytest.raises(ApiException) as exc_info:
        if operation == "speech":
            await media_api.read_aloud(
                media_api.SpeechRequest(task_id=TASK_ID, context="PROMPT", text=""),
                make_request("/api/media/speech"),
                student_user(),
                FakeDb(),  # type: ignore[arg-type]
            )
        else:
            await media_api.generate_task_image(
                TASK_ID,
                make_request(f"/api/teacher/tasks/{TASK_ID}/image"),
                teacher_user(),
                FakeDb(),  # type: ignore[arg-type]
            )

    assert exc_info.value.status_code == 403
    assert expected_feature in exc_info.value.message


def test_inactive_school_pro_falls_back_to_free_entitlements() -> None:
    school = School(
        id=SCHOOL_ID,
        name="Paused Pro School",
        code="PAUSED-PRO",
        plan_code="SCHOOL_PRO",
        subscription_status="PAST_DUE",
    )

    features = features_for_school(school)

    assert features["grammar_check"] is True
    assert features["ai_assist"] is True
    assert features["read_aloud"] is False
    assert features["image_generation"] is False
    assert features["ai_marking"] is False
    assert features["reports"] is False
