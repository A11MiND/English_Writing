import re
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.tasks import serialize_task
from app.core.auth import Role, require_roles, write_audit_log
from app.core.database import get_session
from app.core.responses import ApiException, ErrorCode, success_response
from app.models import (
    Assignment,
    Class,
    ClassMembership,
    Draft,
    ExamEvent,
    StudentProfile,
    Submission,
    User,
    WritingTask,
)
from app.services.marking import create_marking_result_for_submission
from app.services.marking_queue import enqueue_marking_job

router = APIRouter(prefix="/api", tags=["writing"])

SCRIPT_TAG_PATTERN = re.compile(r"<\s*(script|style)[^>]*>.*?<\s*/\s*\1\s*>", re.IGNORECASE | re.DOTALL)
EVENT_ATTR_PATTERN = re.compile(r"\s+on[a-zA-Z]+\s*=\s*(['\"]).*?\1", re.IGNORECASE | re.DOTALL)
JAVASCRIPT_URL_PATTERN = re.compile(r"javascript\s*:", re.IGNORECASE)


class DraftPayload(BaseModel):
    content_html: str = Field(default="", max_length=100_000)
    content_text: str = Field(default="", max_length=100_000)
    word_count: int = Field(ge=0, le=10_000)


class SubmitPayload(BaseModel):
    content_html: str | None = Field(default=None, max_length=100_000)
    content_text: str | None = Field(default=None, max_length=100_000)
    word_count: int | None = Field(default=None, ge=0, le=10_000)


class ExamEventPayload(BaseModel):
    event_type: Literal["PASTE_ATTEMPT", "WINDOW_BLUR", "WINDOW_FOCUS", "FULLSCREEN_EXIT", "SUBMISSION"]
    metadata: dict = Field(default_factory=dict)


def sanitize_html(value: str) -> str:
    without_scripts = SCRIPT_TAG_PATTERN.sub("", value)
    without_event_attrs = EVENT_ATTR_PATTERN.sub("", without_scripts)
    return JAVASCRIPT_URL_PATTERN.sub("", without_event_attrs)


def serialize_draft(row: Draft | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "content_html": row.content_html,
        "content_text": row.content_text,
        "word_count": row.word_count,
        "version": row.version,
        "status": row.status,
        "saved_at": row.saved_at.isoformat(),
    }


def serialize_submission(row: Submission | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "content_html": row.content_html,
        "content_text": row.content_text,
        "word_count": row.word_count,
        "status": row.status,
        "submitted_at": row.submitted_at.isoformat(),
    }


def serialize_exam_event(row: ExamEvent) -> dict:
    return {
        "id": row.id,
        "event_type": row.event_type,
        "metadata": row.event_metadata,
        "occurred_at": row.occurred_at.isoformat(),
    }


async def student_task_context(
    db: AsyncSession, user: User, task_id: str
) -> tuple[StudentProfile, WritingTask, str]:
    profile_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.school_id == user.school_id,
            StudentProfile.user_id == user.id,
        )
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None or profile.current_class_id is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Student class profile not found.", 404)

    task_result = await db.execute(
        select(WritingTask, Class.name)
        .join(Assignment, Assignment.task_id == WritingTask.id)
        .join(Class, Class.id == Assignment.class_id)
        .options(selectinload(WritingTask.rubric))
        .where(
            WritingTask.id == task_id,
            WritingTask.school_id == user.school_id,
            WritingTask.status == "PUBLISHED",
            Assignment.school_id == user.school_id,
            Assignment.class_id == profile.current_class_id,
        )
    )
    row = task_result.one_or_none()
    if row is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Assigned writing task not found.", 404)
    task, class_name = row
    return profile, task, class_name


async def teacher_submission_context(
    db: AsyncSession, user: User, submission_id: str
) -> tuple[Submission, WritingTask, str]:
    result = await db.execute(
        select(Submission, WritingTask, Class.name)
        .join(WritingTask, WritingTask.id == Submission.task_id)
        .join(StudentProfile, StudentProfile.user_id == Submission.student_id)
        .join(Assignment, Assignment.task_id == WritingTask.id)
        .join(Class, Class.id == Assignment.class_id)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .where(
            Submission.id == submission_id,
            Submission.school_id == user.school_id,
            WritingTask.school_id == user.school_id,
            StudentProfile.school_id == user.school_id,
            StudentProfile.current_class_id == Assignment.class_id,
            Assignment.school_id == user.school_id,
            Class.school_id == user.school_id,
            ClassMembership.school_id == user.school_id,
            ClassMembership.user_id == user.id,
            ClassMembership.membership_role == Role.TEACHER,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Submission not found.", 404)
    submission, task, class_name = row
    return submission, task, class_name


async def current_draft_and_submission(
    db: AsyncSession, user: User, task_id: str
) -> tuple[Draft | None, Submission | None]:
    draft_result = await db.execute(
        select(Draft).where(
            Draft.school_id == user.school_id,
            Draft.task_id == task_id,
            Draft.student_id == user.id,
        )
    )
    submission_result = await db.execute(
        select(Submission).where(
            Submission.school_id == user.school_id,
            Submission.task_id == task_id,
            Submission.student_id == user.id,
        )
    )
    return draft_result.scalar_one_or_none(), submission_result.scalar_one_or_none()


def ensure_task_open(task: WritingTask) -> None:
    if task.status in {"CLOSED", "ARCHIVED"}:
        raise ApiException(ErrorCode.TASK_CLOSED, "Writing task is closed.", 409)


@router.get("/student/tasks/{task_id}/writing")
async def get_writing_workspace(
    task_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    _, task, class_name = await student_task_context(db, user, task_id)
    draft, submission = await current_draft_and_submission(db, user, task_id)
    return success_response(
        request,
        {
            "task": serialize_task(task, [class_name]),
            "draft": serialize_draft(draft),
            "submission": serialize_submission(submission),
            "locked": submission is not None,
        },
    )


@router.put("/student/tasks/{task_id}/draft")
async def save_draft(
    task_id: str,
    payload: DraftPayload,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    _, task, _ = await student_task_context(db, user, task_id)
    ensure_task_open(task)
    draft, submission = await current_draft_and_submission(db, user, task_id)
    if submission is not None:
        raise ApiException(ErrorCode.SUBMISSION_LOCKED, "Submission is locked.", 409)

    now = datetime.now(UTC)
    clean_html = sanitize_html(payload.content_html)
    if draft is None:
        draft = Draft(
            school_id=user.school_id,
            task_id=task_id,
            student_id=user.id,
            content_html=clean_html,
            content_text=payload.content_text,
            word_count=payload.word_count,
            version=1,
            status="ACTIVE",
            saved_at=now,
        )
        db.add(draft)
    else:
        draft.content_html = clean_html
        draft.content_text = payload.content_text
        draft.word_count = payload.word_count
        draft.version += 1
        draft.saved_at = now
        draft.updated_at = now

    await db.commit()
    await db.refresh(draft)
    return success_response(request, {"draft": serialize_draft(draft)})


@router.post("/student/tasks/{task_id}/submit")
async def submit_writing(
    task_id: str,
    payload: SubmitPayload,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    _, task, _ = await student_task_context(db, user, task_id)
    ensure_task_open(task)
    draft, existing_submission = await current_draft_and_submission(db, user, task_id)
    if existing_submission is not None:
        raise ApiException(ErrorCode.SUBMISSION_LOCKED, "Submission is locked.", 409)

    content_html = payload.content_html if payload.content_html is not None else draft.content_html if draft else ""
    content_text = payload.content_text if payload.content_text is not None else draft.content_text if draft else ""
    word_count = payload.word_count if payload.word_count is not None else draft.word_count if draft else 0
    submission = Submission(
        school_id=user.school_id,
        task_id=task_id,
        student_id=user.id,
        draft_id=draft.id if draft else None,
        mode=task.mode,
        content_html=sanitize_html(content_html),
        content_text=content_text,
        word_count=word_count,
        status="SUBMITTED",
    )
    db.add(submission)
    await db.flush()
    marking_result = create_marking_result_for_submission(submission)
    db.add(marking_result)
    await db.flush()
    if draft is not None:
        draft.status = "SUBMITTED"
    if task.mode == "EXAM":
        db.add(
            ExamEvent(
                school_id=user.school_id,
                task_id=task_id,
                student_id=user.id,
                event_type="SUBMISSION",
                event_metadata={"source": "manual_or_timer"},
            )
        )
    await write_audit_log(
        db,
        request,
        "WRITING_SUBMITTED",
        user,
        {"task_id": task_id, "mode": task.mode, "word_count": word_count},
    )
    await db.commit()
    await db.refresh(submission)
    marking_job_enqueued = True
    try:
        await enqueue_marking_job(marking_result.id)
    except Exception:
        marking_job_enqueued = False
    return success_response(
        request,
        {
            "submission": serialize_submission(submission),
            "locked": True,
            "marking_job": {
                "id": marking_result.id,
                "status": marking_result.status,
                "enqueued": marking_job_enqueued,
            },
        },
    )


@router.post("/student/tasks/{task_id}/exam-events")
async def record_exam_event(
    task_id: str,
    payload: ExamEventPayload,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    _, task, _ = await student_task_context(db, user, task_id)
    if task.mode != "EXAM":
        raise ApiException(ErrorCode.ACCESS_DENIED, "Exam events are allowed for Exam Mode only.", 403)
    event = ExamEvent(
        school_id=user.school_id,
        task_id=task_id,
        student_id=user.id,
        event_type=payload.event_type,
        event_metadata=payload.metadata,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return success_response(
        request,
        {
            "event": {
                "id": event.id,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at.isoformat(),
            }
        },
    )


@router.get("/teacher/submissions/{submission_id}/exam-events")
async def list_teacher_submission_exam_events(
    submission_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    submission, task, class_name = await teacher_submission_context(db, user, submission_id)
    result = await db.execute(
        select(ExamEvent)
        .where(
            ExamEvent.school_id == user.school_id,
            ExamEvent.task_id == task.id,
            ExamEvent.student_id == submission.student_id,
        )
        .order_by(ExamEvent.occurred_at.asc())
    )
    return success_response(
        request,
        {
            "submission_id": submission.id,
            "task_id": task.id,
            "mode": task.mode,
            "class_name": class_name,
            "events": [serialize_exam_event(row) for row in result.scalars().all()],
        },
    )
