from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import Role, require_roles, write_audit_log
from app.core.database import get_session
from app.core.responses import ApiException, ErrorCode, success_response
from app.models import (
    Assignment,
    Class,
    ClassMembership,
    MarkingResult,
    PostWritingExercise,
    StudentProfile,
    Submission,
    TeacherReview,
    User,
    WritingTask,
)
from app.services.marking import (
    create_exercises_for_marking_result,
    process_marking_result,
    serialize_marking_result,
)

router = APIRouter(prefix="/api", tags=["marking"])


class TeacherReviewPayload(BaseModel):
    content_score: int | None = Field(default=None, ge=0, le=5)
    language_score: int | None = Field(default=None, ge=0, le=5)
    organisation_score: int | None = Field(default=None, ge=0, le=5)
    total_score: int | None = Field(default=None, ge=0, le=15)
    review_notes: str | None = Field(default=None, max_length=5000)
    status: str = Field(default="REVIEWED", pattern="^(DRAFT|REVIEWED|RELEASE_READY)$")

    @model_validator(mode="after")
    def validate_total(self) -> "TeacherReviewPayload":
        scores = [self.content_score, self.language_score, self.organisation_score]
        if all(score is not None for score in scores):
            calculated_total = sum(score or 0 for score in scores)
            if self.total_score is None:
                self.total_score = calculated_total
            elif self.total_score != calculated_total:
                raise ValueError("total_score must equal the sum of dimension scores.")
        return self


def serialize_submission_for_marking(
    submission: Submission,
    task: WritingTask,
    class_name: str,
    marking_result: MarkingResult | None,
) -> dict:
    return {
        "submission": {
            "id": submission.id,
            "task_id": submission.task_id,
            "student_id": submission.student_id,
            "content_text": submission.content_text,
            "word_count": submission.word_count,
            "status": submission.status,
            "submitted_at": submission.submitted_at.isoformat(),
        },
        "task": {
            "id": task.id,
            "title": task.title,
            "mode": task.mode,
            "level": task.level,
        },
        "class_name": class_name,
        "marking_result": serialize_marking_result(marking_result),
    }


async def teacher_marking_context(
    db: AsyncSession, teacher: User, marking_result_id: str
) -> tuple[MarkingResult, Submission, WritingTask, str]:
    result = await db.execute(
        select(MarkingResult, Submission, WritingTask, Class.name)
        .join(Submission, Submission.id == MarkingResult.submission_id)
        .join(WritingTask, WritingTask.id == Submission.task_id)
        .join(Assignment, Assignment.task_id == WritingTask.id)
        .join(
            StudentProfile,
            (StudentProfile.user_id == Submission.student_id)
            & (StudentProfile.current_class_id == Assignment.class_id),
        )
        .join(Class, Class.id == Assignment.class_id)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .where(
            MarkingResult.id == marking_result_id,
            MarkingResult.school_id == teacher.school_id,
            StudentProfile.school_id == teacher.school_id,
            Submission.school_id == teacher.school_id,
            WritingTask.school_id == teacher.school_id,
            Assignment.school_id == teacher.school_id,
            ClassMembership.school_id == teacher.school_id,
            ClassMembership.user_id == teacher.id,
            ClassMembership.membership_role == Role.TEACHER,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Marking result not found.", 404)
    return row


@router.get("/teacher/marking/submissions")
async def list_teacher_marking_submissions(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
    class_id: Annotated[str | None, Query()] = None,
    task_id: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> dict:
    statement = (
        select(Submission, WritingTask, Class.name, MarkingResult)
        .join(WritingTask, WritingTask.id == Submission.task_id)
        .join(Assignment, Assignment.task_id == WritingTask.id)
        .join(
            StudentProfile,
            (StudentProfile.user_id == Submission.student_id)
            & (StudentProfile.current_class_id == Assignment.class_id),
        )
        .join(Class, Class.id == Assignment.class_id)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .outerjoin(MarkingResult, MarkingResult.submission_id == Submission.id)
        .where(
            Submission.school_id == user.school_id,
            StudentProfile.school_id == user.school_id,
            WritingTask.school_id == user.school_id,
            Assignment.school_id == user.school_id,
            ClassMembership.school_id == user.school_id,
            ClassMembership.user_id == user.id,
            ClassMembership.membership_role == Role.TEACHER,
        )
        .order_by(Submission.submitted_at.desc())
    )
    if class_id:
        statement = statement.where(Class.id == class_id)
    if task_id:
        statement = statement.where(WritingTask.id == task_id)
    if status:
        statement = statement.where(MarkingResult.status == status)
    result = await db.execute(statement)
    rows = [
        serialize_submission_for_marking(submission, task, class_name, marking_result)
        for submission, task, class_name, marking_result in result.all()
    ]
    return success_response(request, {"items": rows})


@router.get("/teacher/dashboard-summary")
async def get_teacher_dashboard_summary(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
    class_id: Annotated[str | None, Query()] = None,
    task_id: Annotated[str | None, Query()] = None,
) -> dict:
    base_filters = [
        Submission.school_id == user.school_id,
        StudentProfile.school_id == user.school_id,
        WritingTask.school_id == user.school_id,
        Assignment.school_id == user.school_id,
        ClassMembership.school_id == user.school_id,
        ClassMembership.user_id == user.id,
        ClassMembership.membership_role == Role.TEACHER,
    ]
    if class_id:
        base_filters.append(Class.id == class_id)
    if task_id:
        base_filters.append(WritingTask.id == task_id)

    submission_statement = (
        select(
            func.count(func.distinct(Submission.id)).label("submitted_count"),
            func.count(func.distinct(WritingTask.id)).label("task_count"),
            func.count(func.distinct(Class.id)).label("class_count"),
        )
        .select_from(Submission)
        .join(WritingTask, WritingTask.id == Submission.task_id)
        .join(Assignment, Assignment.task_id == WritingTask.id)
        .join(
            StudentProfile,
            (StudentProfile.user_id == Submission.student_id)
            & (StudentProfile.current_class_id == Assignment.class_id),
        )
        .join(Class, Class.id == Assignment.class_id)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .where(*base_filters)
    )
    submission_row = (await db.execute(submission_statement)).one()

    status_statement = (
        select(MarkingResult.status, func.count(func.distinct(MarkingResult.id)))
        .select_from(MarkingResult)
        .join(Submission, Submission.id == MarkingResult.submission_id)
        .join(WritingTask, WritingTask.id == Submission.task_id)
        .join(Assignment, Assignment.task_id == WritingTask.id)
        .join(
            StudentProfile,
            (StudentProfile.user_id == Submission.student_id)
            & (StudentProfile.current_class_id == Assignment.class_id),
        )
        .join(Class, Class.id == Assignment.class_id)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .where(*base_filters, MarkingResult.school_id == user.school_id)
        .group_by(MarkingResult.status)
    )
    marking_counts = {
        status: count for status, count in (await db.execute(status_statement)).all()
    }

    unreleased_statement = (
        select(func.count(func.distinct(MarkingResult.id)))
        .select_from(MarkingResult)
        .join(Submission, Submission.id == MarkingResult.submission_id)
        .join(WritingTask, WritingTask.id == Submission.task_id)
        .join(Assignment, Assignment.task_id == WritingTask.id)
        .join(
            StudentProfile,
            (StudentProfile.user_id == Submission.student_id)
            & (StudentProfile.current_class_id == Assignment.class_id),
        )
        .join(Class, Class.id == Assignment.class_id)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .outerjoin(TeacherReview, TeacherReview.marking_result_id == MarkingResult.id)
        .where(
            *base_filters,
            MarkingResult.school_id == user.school_id,
            MarkingResult.status == "AI_MARKED",
            or_(TeacherReview.id.is_(None), TeacherReview.status != "RELEASED"),
        )
    )
    unreleased_feedback_count = (await db.execute(unreleased_statement)).scalar_one()

    return success_response(
        request,
        {
            "summary": {
                "assigned_class_count": submission_row.class_count,
                "active_task_count": submission_row.task_count,
                "submitted_count": submission_row.submitted_count,
                "pending_marking_count": sum(
                    marking_counts.get(status, 0)
                    for status in ["QUEUED", "PROCESSING", "AI_MARKING_FAILED"]
                ),
                "unreleased_feedback_count": unreleased_feedback_count,
                "marking_status_counts": {
                    "QUEUED": marking_counts.get("QUEUED", 0),
                    "PROCESSING": marking_counts.get("PROCESSING", 0),
                    "AI_MARKED": marking_counts.get("AI_MARKED", 0),
                    "AI_MARKING_FAILED": marking_counts.get("AI_MARKING_FAILED", 0),
                },
            }
        },
    )


@router.post("/teacher/marking-results/{marking_result_id}/run")
async def run_teacher_marking_result(
    marking_result_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    marking_result, _, _, _ = await teacher_marking_context(db, user, marking_result_id)
    if marking_result.status == "AI_MARKED":
        return success_response(request, {"marking_result": serialize_marking_result(marking_result)})
    await process_marking_result(db, marking_result)
    await write_audit_log(
        db,
        request,
        "AI_MARKING_RUN",
        user,
        {"marking_result_id": marking_result.id, "status": marking_result.status},
    )
    await db.commit()
    await db.refresh(marking_result)
    return success_response(request, {"marking_result": serialize_marking_result(marking_result)})


@router.post("/teacher/marking-results/{marking_result_id}/retry")
async def retry_teacher_marking_result(
    marking_result_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    marking_result, _, _, _ = await teacher_marking_context(db, user, marking_result_id)
    if marking_result.status != "AI_MARKING_FAILED":
        raise ApiException(ErrorCode.VALIDATION_ERROR, "Only failed AI marking can be retried.", 422)
    marking_result.status = "QUEUED"
    marking_result.last_error = None
    marking_result.updated_at = datetime.now(UTC)
    await process_marking_result(db, marking_result)
    await write_audit_log(
        db,
        request,
        "AI_MARKING_RETRIED",
        user,
        {"marking_result_id": marking_result.id, "status": marking_result.status},
    )
    await db.commit()
    await db.refresh(marking_result)
    return success_response(request, {"marking_result": serialize_marking_result(marking_result)})


@router.post("/teacher/marking-results/{marking_result_id}/review")
async def review_teacher_marking_result(
    marking_result_id: str,
    payload: TeacherReviewPayload,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    marking_result, submission, _, _ = await teacher_marking_context(db, user, marking_result_id)
    existing_result = await db.execute(
        select(TeacherReview).where(
            TeacherReview.school_id == user.school_id,
            TeacherReview.marking_result_id == marking_result_id,
        )
    )
    review = existing_result.scalar_one_or_none()
    if review is None:
        review = TeacherReview(
            school_id=user.school_id,
            marking_result_id=marking_result_id,
            submission_id=submission.id,
            teacher_id=user.id,
        )
        db.add(review)

    review.content_score = payload.content_score
    review.language_score = payload.language_score
    review.organisation_score = payload.organisation_score
    review.total_score = payload.total_score
    review.review_notes = payload.review_notes
    review.status = payload.status
    review.updated_at = datetime.now(UTC)

    await write_audit_log(
        db,
        request,
        "TEACHER_MARKING_OVERRIDE",
        user,
        {
            "marking_result_id": marking_result.id,
            "submission_id": submission.id,
            "content_score": payload.content_score,
            "language_score": payload.language_score,
            "organisation_score": payload.organisation_score,
            "total_score": payload.total_score,
        },
    )
    await db.commit()
    await db.refresh(review)
    return success_response(
        request,
        {
            "review": serialize_teacher_review(review)
        },
    )


def serialize_teacher_review(row: TeacherReview) -> dict:
    return {
        "id": row.id,
        "marking_result_id": row.marking_result_id,
        "submission_id": row.submission_id,
        "content_score": row.content_score,
        "language_score": row.language_score,
        "organisation_score": row.organisation_score,
        "total_score": row.total_score,
        "review_notes": row.review_notes,
        "status": row.status,
        "feedback_released_at": row.feedback_released_at.isoformat() if row.feedback_released_at else None,
    }


def serialize_exercise(row: PostWritingExercise) -> dict:
    return {
        "id": row.id,
        "marking_result_id": row.marking_result_id,
        "submission_id": row.submission_id,
        "title": row.title,
        "exercise_type": row.exercise_type,
        "focus_area": row.focus_area,
        "prompt": row.prompt,
        "response_text": row.response_text,
        "status": row.status,
        "assigned_at": row.assigned_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


@router.post("/teacher/marking-results/{marking_result_id}/release")
async def release_teacher_feedback(
    marking_result_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    marking_result, submission, _, _ = await teacher_marking_context(db, user, marking_result_id)
    if marking_result.status != "AI_MARKED":
        raise ApiException(ErrorCode.VALIDATION_ERROR, "Only marked submissions can be released.", 422)

    existing_result = await db.execute(
        select(TeacherReview).where(
            TeacherReview.school_id == user.school_id,
            TeacherReview.marking_result_id == marking_result_id,
        )
    )
    review = existing_result.scalar_one_or_none()
    if review is None:
        review = TeacherReview(
            school_id=user.school_id,
            marking_result_id=marking_result_id,
            submission_id=submission.id,
            teacher_id=user.id,
            content_score=marking_result.content_score,
            language_score=marking_result.language_score,
            organisation_score=marking_result.organisation_score,
            total_score=marking_result.total_score,
        )
        db.add(review)

    review.status = "RELEASED"
    review.feedback_released_at = datetime.now(UTC)
    review.feedback_released_by = user.id
    review.updated_at = datetime.now(UTC)
    await create_exercises_for_marking_result(db, marking_result)

    await write_audit_log(
        db,
        request,
        "FEEDBACK_RELEASED",
        user,
        {"marking_result_id": marking_result.id, "submission_id": submission.id},
    )
    await db.commit()
    await db.refresh(review)
    return success_response(request, {"review": serialize_teacher_review(review)})


@router.get("/student/submissions/{submission_id}/feedback")
async def get_student_feedback(
    submission_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    result = await db.execute(
        select(Submission, MarkingResult, TeacherReview, WritingTask)
        .join(MarkingResult, MarkingResult.submission_id == Submission.id)
        .join(TeacherReview, TeacherReview.marking_result_id == MarkingResult.id)
        .join(WritingTask, WritingTask.id == Submission.task_id)
        .where(
            Submission.id == submission_id,
            Submission.school_id == user.school_id,
            Submission.student_id == user.id,
            MarkingResult.school_id == user.school_id,
            TeacherReview.school_id == user.school_id,
            TeacherReview.status == "RELEASED",
            TeacherReview.feedback_released_at.is_not(None),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Released feedback not found.", 404)
    submission, marking_result, review, task = row

    exercise_result = await db.execute(
        select(PostWritingExercise)
        .where(
            PostWritingExercise.school_id == user.school_id,
            PostWritingExercise.submission_id == submission_id,
            PostWritingExercise.student_id == user.id,
        )
        .order_by(PostWritingExercise.assigned_at)
    )
    return success_response(
        request,
        {
            "task": {"id": task.id, "title": task.title, "mode": task.mode, "level": task.level},
            "submission": {
                "id": submission.id,
                "content_text": submission.content_text,
                "word_count": submission.word_count,
                "submitted_at": submission.submitted_at.isoformat(),
            },
            "marking_result": serialize_marking_result(marking_result),
            "review": serialize_teacher_review(review),
            "exercises": [serialize_exercise(exercise) for exercise in exercise_result.scalars().all()],
        },
    )


class CompleteExercisePayload(BaseModel):
    response_text: str = Field(min_length=1, max_length=10_000)


@router.post("/student/exercises/{exercise_id}/complete")
async def complete_student_exercise(
    exercise_id: str,
    payload: CompleteExercisePayload,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    result = await db.execute(
        select(PostWritingExercise)
        .join(TeacherReview, TeacherReview.submission_id == PostWritingExercise.submission_id)
        .where(
            PostWritingExercise.id == exercise_id,
            PostWritingExercise.school_id == user.school_id,
            PostWritingExercise.student_id == user.id,
            TeacherReview.school_id == user.school_id,
            TeacherReview.status == "RELEASED",
            TeacherReview.feedback_released_at.is_not(None),
        )
    )
    exercise = result.scalar_one_or_none()
    if exercise is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Exercise not found.", 404)

    exercise.response_text = payload.response_text
    exercise.status = "COMPLETED"
    exercise.completed_at = datetime.now(UTC)
    exercise.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(exercise)
    return success_response(request, {"exercise": serialize_exercise(exercise)})
