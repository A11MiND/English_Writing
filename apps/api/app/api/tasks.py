from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import Role, require_roles, write_audit_log
from app.core.database import get_session
from app.core.responses import ApiException, ErrorCode, success_response
from app.models import (
    Assignment,
    Class,
    ClassMembership,
    Draft,
    MarkingResult,
    Rubric,
    RubricDimension,
    StudentProfile,
    Submission,
    TeacherReview,
    User,
    WritingTask,
)

router = APIRouter(prefix="/api", tags=["tasks"])

SUPPORTED_LEVELS = {"P4", "P5", "P6"}
REQUIRED_DIMENSIONS = {"Content", "Language", "Organisation"}


class RubricDimensionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    min_score: int = Field(ge=0, le=100)
    max_score: int = Field(ge=1, le=100)
    descriptor: str = Field(min_length=1, max_length=2000)
    sort_order: int = Field(ge=1, le=20)

    @field_validator("name", "descriptor")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validate_score_range(self) -> "RubricDimensionRequest":
        if self.max_score <= self.min_score:
            raise ValueError("max_score must be greater than min_score.")
        return self


class CreateRubricRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    level: str = Field(min_length=2, max_length=16)
    total_score: int = Field(ge=1, le=100)
    status: Literal["DRAFT", "ACTIVE"] = "ACTIVE"
    dimensions: list[RubricDimensionRequest] = Field(min_length=3, max_length=10)

    @field_validator("title", "level")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in SUPPORTED_LEVELS:
            raise ValueError("Level must be P4, P5 or P6.")
        return normalized

    @model_validator(mode="after")
    def validate_dimensions(self) -> "CreateRubricRequest":
        names = {dimension.name for dimension in self.dimensions}
        if not REQUIRED_DIMENSIONS.issubset(names):
            raise ValueError("Rubric must include Content, Language and Organisation.")
        if sum(dimension.max_score for dimension in self.dimensions) != self.total_score:
            raise ValueError("Total score must equal the sum of dimension max scores.")
        return self


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    level: str = Field(min_length=2, max_length=16)
    instruction: str = Field(min_length=1, max_length=5000)
    genre: str | None = Field(default=None, max_length=64)
    mode: Literal["PRACTICE", "EXAM"]
    word_minimum: int | None = Field(default=None, ge=0, le=2000)
    word_maximum: int | None = Field(default=None, ge=1, le=3000)
    due_at: datetime | None = None
    exam_duration_minutes: int | None = Field(default=None, ge=1, le=240)
    rubric_id: str = Field(min_length=36, max_length=36)
    status: Literal["DRAFT", "PUBLISHED"] = "DRAFT"

    @field_validator("title", "level", "instruction", "genre")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in SUPPORTED_LEVELS:
            raise ValueError("Level must be P4, P5 or P6.")
        return normalized

    @model_validator(mode="after")
    def validate_word_limits(self) -> "CreateTaskRequest":
        if (
            self.word_minimum is not None
            and self.word_maximum is not None
            and self.word_maximum < self.word_minimum
        ):
            raise ValueError("word_maximum must be greater than or equal to word_minimum.")
        if self.mode == "EXAM" and self.exam_duration_minutes is None:
            raise ValueError("exam_duration_minutes is required for Exam Mode tasks.")
        if self.mode == "PRACTICE" and self.exam_duration_minutes is not None:
            raise ValueError("Practice Mode tasks must not set exam_duration_minutes.")
        return self


class UpdateRubricRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    level: str | None = Field(default=None, min_length=2, max_length=16)
    total_score: int | None = Field(default=None, ge=1, le=100)
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"] | None = None
    dimensions: list[RubricDimensionRequest] | None = Field(default=None, min_length=3, max_length=10)

    @field_validator("title", "level")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in SUPPORTED_LEVELS:
            raise ValueError("Level must be P4, P5 or P6.")
        return normalized

    @model_validator(mode="after")
    def validate_dimensions(self) -> "UpdateRubricRequest":
        if self.dimensions is None:
            return self
        if self.total_score is None:
            raise ValueError("total_score is required when replacing rubric dimensions.")
        names = {dimension.name for dimension in self.dimensions}
        if not REQUIRED_DIMENSIONS.issubset(names):
            raise ValueError("Rubric must include Content, Language and Organisation.")
        if sum(dimension.max_score for dimension in self.dimensions) != self.total_score:
            raise ValueError("Total score must equal the sum of dimension max scores.")
        return self


class DuplicateRubricRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class UpdateTaskRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    level: str | None = Field(default=None, min_length=2, max_length=16)
    instruction: str | None = Field(default=None, min_length=1, max_length=5000)
    genre: str | None = Field(default=None, max_length=64)
    mode: Literal["PRACTICE", "EXAM"] | None = None
    word_minimum: int | None = Field(default=None, ge=0, le=2000)
    word_maximum: int | None = Field(default=None, ge=1, le=3000)
    due_at: datetime | None = None
    exam_duration_minutes: int | None = Field(default=None, ge=1, le=240)
    rubric_id: str | None = Field(default=None, min_length=36, max_length=36)
    status: Literal["DRAFT", "PUBLISHED", "CLOSED", "ARCHIVED"] | None = None

    @field_validator("title", "level", "instruction", "genre")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if normalized not in SUPPORTED_LEVELS:
            raise ValueError("Level must be P4, P5 or P6.")
        return normalized

    @model_validator(mode="after")
    def validate_word_limits(self) -> "UpdateTaskRequest":
        if (
            self.word_minimum is not None
            and self.word_maximum is not None
            and self.word_maximum < self.word_minimum
        ):
            raise ValueError("word_maximum must be greater than or equal to word_minimum.")
        return self


class AssignTaskRequest(BaseModel):
    class_id: str = Field(min_length=36, max_length=36)


def serialize_dimension(row: RubricDimension) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "min_score": row.min_score,
        "max_score": row.max_score,
        "descriptor": row.descriptor,
        "sort_order": row.sort_order,
    }


def serialize_rubric(row: Rubric, used_by_task_count: int = 0) -> dict:
    dimensions = sorted(row.dimensions, key=lambda dimension: dimension.sort_order)
    return {
        "id": row.id,
        "title": row.title,
        "level": row.level,
        "total_score": row.total_score,
        "status": row.status,
        "used_by_task_count": used_by_task_count,
        "dimensions": [serialize_dimension(dimension) for dimension in dimensions],
    }


def serialize_task(row: WritingTask, class_names: list[str] | None = None) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "level": row.level,
        "instruction": row.instruction,
        "genre": row.genre,
        "mode": row.mode,
        "word_minimum": row.word_minimum,
        "word_maximum": row.word_maximum,
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "exam_duration_minutes": row.exam_duration_minutes,
        "rubric_id": row.rubric_id,
        "rubric_title": row.rubric.title if row.rubric else None,
        "status": row.status,
        "assigned_classes": class_names or [],
    }


def add_student_task_state(
    task_payload: dict,
    draft: Draft | None,
    submission: Submission | None,
    review: TeacherReview | None,
) -> dict:
    task_payload["draft_status"] = draft.status if draft else None
    task_payload["draft_saved_at"] = draft.saved_at.isoformat() if draft else None
    task_payload["submission_id"] = submission.id if submission else None
    task_payload["submission_status"] = submission.status if submission else None
    task_payload["submitted_at"] = submission.submitted_at.isoformat() if submission else None
    task_payload["locked"] = submission is not None
    task_payload["feedback_released"] = (
        review is not None and review.status == "RELEASED" and review.feedback_released_at is not None
    )
    return task_payload


async def ensure_teacher_assigned_to_class(
    db: AsyncSession, teacher: User, class_id: str
) -> Class:
    result = await db.execute(
        select(Class)
        .join(ClassMembership, ClassMembership.class_id == Class.id)
        .where(
            Class.id == class_id,
            Class.school_id == teacher.school_id,
            ClassMembership.school_id == teacher.school_id,
            ClassMembership.user_id == teacher.id,
            ClassMembership.membership_role == Role.TEACHER,
        )
    )
    class_row = result.scalar_one_or_none()
    if class_row is None:
        raise ApiException(ErrorCode.ACCESS_DENIED, "Teacher is not assigned to this class.", 403)
    return class_row


async def teacher_rubric_or_404(db: AsyncSession, teacher: User, rubric_id: str) -> Rubric:
    result = await db.execute(
        select(Rubric)
        .options(selectinload(Rubric.dimensions))
        .where(
            Rubric.id == rubric_id,
            Rubric.school_id == teacher.school_id,
            Rubric.created_by == teacher.id,
        )
    )
    rubric = result.scalar_one_or_none()
    if rubric is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Rubric not found.", 404)
    return rubric


async def teacher_task_or_404(db: AsyncSession, teacher: User, task_id: str) -> WritingTask:
    result = await db.execute(
        select(WritingTask)
        .options(selectinload(WritingTask.rubric))
        .where(
            WritingTask.id == task_id,
            WritingTask.school_id == teacher.school_id,
            WritingTask.created_by == teacher.id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Writing task not found.", 404)
    return task


async def rubric_is_used(db: AsyncSession, teacher: User, rubric_id: str) -> bool:
    result = await db.execute(
        select(WritingTask.id).where(
            WritingTask.school_id == teacher.school_id,
            WritingTask.rubric_id == rubric_id,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def rubric_task_count(db: AsyncSession, teacher: User, rubric_id: str) -> int:
    result = await db.execute(
        select(func.count(WritingTask.id)).where(
            WritingTask.school_id == teacher.school_id,
            WritingTask.rubric_id == rubric_id,
        )
    )
    return int(result.scalar_one())


async def task_assignment_class_names(db: AsyncSession, school_id: str, task_id: str) -> list[str]:
    result = await db.execute(
        select(Class.name)
        .join(Assignment, Assignment.class_id == Class.id)
        .where(
            Assignment.school_id == school_id,
            Assignment.task_id == task_id,
            Class.school_id == school_id,
        )
        .order_by(Class.name)
    )
    return list(result.scalars().all())


async def task_has_submission(db: AsyncSession, teacher: User, task_id: str) -> bool:
    result = await db.execute(
        select(Submission.id).where(
            Submission.school_id == teacher.school_id,
            Submission.task_id == task_id,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


@router.get("/teacher/rubrics")
async def list_teacher_rubrics(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    result = await db.execute(
        select(Rubric)
        .options(selectinload(Rubric.dimensions))
        .where(Rubric.school_id == user.school_id, Rubric.status != "ARCHIVED")
        .order_by(Rubric.level, Rubric.title)
    )
    rubrics = result.scalars().all()
    count_result = await db.execute(
        select(WritingTask.rubric_id, func.count(WritingTask.id))
        .where(
            WritingTask.school_id == user.school_id,
            WritingTask.rubric_id.in_([rubric.id for rubric in rubrics] or [""]),
        )
        .group_by(WritingTask.rubric_id)
    )
    counts_by_rubric = {rubric_id: int(count) for rubric_id, count in count_result}
    return success_response(
        request,
        {
            "rubrics": [
                serialize_rubric(row, counts_by_rubric.get(row.id, 0)) for row in rubrics
            ]
        },
    )


@router.post("/teacher/rubrics")
async def create_teacher_rubric(
    payload: CreateRubricRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    rubric = Rubric(
        school_id=user.school_id,
        title=payload.title,
        level=payload.level,
        total_score=payload.total_score,
        status=payload.status,
        created_by=user.id,
    )
    db.add(rubric)
    await db.flush()

    for dimension in payload.dimensions:
        db.add(
            RubricDimension(
                school_id=user.school_id,
                rubric_id=rubric.id,
                name=dimension.name,
                min_score=dimension.min_score,
                max_score=dimension.max_score,
                descriptor=dimension.descriptor,
                sort_order=dimension.sort_order,
            )
        )

    await write_audit_log(
        db,
        request,
        "RUBRIC_CREATED",
        user,
        {"rubric_title": payload.title, "level": payload.level},
    )
    await db.commit()

    result = await db.execute(
        select(Rubric).options(selectinload(Rubric.dimensions)).where(Rubric.id == rubric.id)
    )
    return success_response(request, {"rubric": serialize_rubric(result.scalar_one())})


@router.patch("/teacher/rubrics/{rubric_id}")
async def update_teacher_rubric(
    rubric_id: str,
    payload: UpdateRubricRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    rubric = await teacher_rubric_or_404(db, user, rubric_id)
    is_used = await rubric_is_used(db, user, rubric_id)
    requested = payload.model_dump(exclude_unset=True)
    requested_keys = set(requested.keys())
    if is_used and requested_keys - {"status"}:
        raise ApiException(
            ErrorCode.VALIDATION_ERROR,
            "Rubric has been used by a writing task. Duplicate it before changing content or scores.",
            422,
        )

    if payload.title is not None:
        rubric.title = payload.title
    if payload.level is not None:
        rubric.level = payload.level
    if payload.total_score is not None:
        rubric.total_score = payload.total_score
    if payload.status is not None:
        rubric.status = payload.status
    if payload.dimensions is not None:
        for existing in list(rubric.dimensions):
            await db.delete(existing)
        await db.flush()
        for dimension in payload.dimensions:
            db.add(
                RubricDimension(
                    school_id=user.school_id,
                    rubric_id=rubric.id,
                    name=dimension.name,
                    min_score=dimension.min_score,
                    max_score=dimension.max_score,
                    descriptor=dimension.descriptor,
                    sort_order=dimension.sort_order,
                )
            )

    await write_audit_log(
        db,
        request,
        "RUBRIC_UPDATED",
        user,
        {"rubric_id": rubric_id, "changed_fields": sorted(requested_keys)},
    )
    await db.commit()

    result = await db.execute(
        select(Rubric).options(selectinload(Rubric.dimensions)).where(Rubric.id == rubric.id)
    )
    return success_response(
        request,
        {
            "rubric": serialize_rubric(
                result.scalar_one(),
                await rubric_task_count(db, user, rubric_id),
            )
        },
    )


@router.post("/teacher/rubrics/{rubric_id}/duplicate")
async def duplicate_teacher_rubric(
    rubric_id: str,
    payload: DuplicateRubricRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    source = await teacher_rubric_or_404(db, user, rubric_id)
    duplicate = Rubric(
        school_id=user.school_id,
        title=payload.title or f"{source.title} Copy",
        level=source.level,
        total_score=source.total_score,
        status="DRAFT",
        created_by=user.id,
    )
    db.add(duplicate)
    await db.flush()
    for dimension in source.dimensions:
        db.add(
            RubricDimension(
                school_id=user.school_id,
                rubric_id=duplicate.id,
                name=dimension.name,
                min_score=dimension.min_score,
                max_score=dimension.max_score,
                descriptor=dimension.descriptor,
                sort_order=dimension.sort_order,
            )
        )

    await write_audit_log(
        db,
        request,
        "RUBRIC_DUPLICATED",
        user,
        {"source_rubric_id": rubric_id, "rubric_title": duplicate.title},
    )
    await db.commit()

    result = await db.execute(
        select(Rubric).options(selectinload(Rubric.dimensions)).where(Rubric.id == duplicate.id)
    )
    return success_response(request, {"rubric": serialize_rubric(result.scalar_one())})


@router.get("/teacher/tasks")
async def list_teacher_tasks(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    result = await db.execute(
        select(WritingTask)
        .options(selectinload(WritingTask.rubric))
        .where(WritingTask.school_id == user.school_id, WritingTask.created_by == user.id)
        .order_by(WritingTask.created_at.desc())
    )
    tasks = result.scalars().all()

    assignment_result = await db.execute(
        select(Assignment.task_id, Class.name)
        .join(Class, Class.id == Assignment.class_id)
        .where(Assignment.school_id == user.school_id, Assignment.task_id.in_([task.id for task in tasks] or [""]))
    )
    class_names_by_task: dict[str, list[str]] = {}
    for task_id, class_name in assignment_result:
        class_names_by_task.setdefault(task_id, []).append(class_name)

    return success_response(
        request,
        {"tasks": [serialize_task(task, class_names_by_task.get(task.id, [])) for task in tasks]},
    )


@router.get("/teacher/tasks/{task_id}")
async def get_teacher_task(
    task_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    task = await teacher_task_or_404(db, user, task_id)
    class_names = await task_assignment_class_names(db, user.school_id, task_id)
    return success_response(request, {"task": serialize_task(task, class_names)})


@router.post("/teacher/tasks")
async def create_teacher_task(
    payload: CreateTaskRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    rubric_result = await db.execute(
        select(Rubric).where(
            Rubric.id == payload.rubric_id,
            Rubric.school_id == user.school_id,
            Rubric.status != "ARCHIVED",
        )
    )
    rubric = rubric_result.scalar_one_or_none()
    if rubric is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Rubric not found.", 404)

    task = WritingTask(
        school_id=user.school_id,
        title=payload.title,
        level=payload.level,
        instruction=payload.instruction,
        genre=payload.genre,
        mode=payload.mode,
        word_minimum=payload.word_minimum,
        word_maximum=payload.word_maximum,
        due_at=payload.due_at,
        exam_duration_minutes=payload.exam_duration_minutes,
        rubric_id=payload.rubric_id,
        created_by=user.id,
        status=payload.status,
    )
    db.add(task)
    await write_audit_log(
        db,
        request,
        "WRITING_TASK_CREATED",
        user,
        {"task_title": payload.title, "mode": payload.mode, "status": payload.status},
    )
    await db.commit()
    await db.refresh(task)
    task.rubric = rubric
    return success_response(request, {"task": serialize_task(task)})


@router.patch("/teacher/tasks/{task_id}")
async def update_teacher_task(
    task_id: str,
    payload: UpdateTaskRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    task = await teacher_task_or_404(db, user, task_id)
    has_submission = await task_has_submission(db, user, task_id)
    requested = payload.model_dump(exclude_unset=True)
    requested_keys = set(requested.keys())
    if has_submission and requested_keys - {"status"}:
        raise ApiException(
            ErrorCode.VALIDATION_ERROR,
            "Task already has submissions. Only status can be changed.",
            422,
        )

    if payload.rubric_id is not None and payload.rubric_id != task.rubric_id:
        rubric_result = await db.execute(
            select(Rubric).where(
                Rubric.id == payload.rubric_id,
                Rubric.school_id == user.school_id,
                Rubric.status != "ARCHIVED",
            )
        )
        if rubric_result.scalar_one_or_none() is None:
            raise ApiException(ErrorCode.NOT_FOUND, "Rubric not found.", 404)
        task.rubric_id = payload.rubric_id

    if payload.title is not None:
        task.title = payload.title
    if payload.level is not None:
        task.level = payload.level
    if payload.instruction is not None:
        task.instruction = payload.instruction
    if "genre" in requested:
        task.genre = payload.genre
    if payload.mode is not None:
        task.mode = payload.mode
    if "word_minimum" in requested:
        task.word_minimum = payload.word_minimum
    if "word_maximum" in requested:
        task.word_maximum = payload.word_maximum
    if "due_at" in requested:
        task.due_at = payload.due_at
    if "exam_duration_minutes" in requested:
        task.exam_duration_minutes = payload.exam_duration_minutes
    if payload.status is not None:
        task.status = payload.status

    final_mode = payload.mode or task.mode
    if final_mode == "EXAM" and task.exam_duration_minutes is None:
        raise ApiException(
            ErrorCode.VALIDATION_ERROR,
            "exam_duration_minutes is required for Exam Mode tasks.",
            422,
        )
    if final_mode == "PRACTICE" and task.exam_duration_minutes is not None:
        task.exam_duration_minutes = None

    await write_audit_log(
        db,
        request,
        "WRITING_TASK_UPDATED",
        user,
        {"task_id": task_id, "changed_fields": sorted(requested_keys)},
    )
    await db.commit()

    result = await db.execute(
        select(WritingTask)
        .options(selectinload(WritingTask.rubric))
        .where(WritingTask.id == task.id)
    )
    return success_response(request, {"task": serialize_task(result.scalar_one())})


@router.post("/teacher/tasks/{task_id}/assignments")
async def assign_teacher_task(
    task_id: str,
    payload: AssignTaskRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    task_result = await db.execute(
        select(WritingTask)
        .options(selectinload(WritingTask.rubric))
        .where(
            WritingTask.id == task_id,
            WritingTask.school_id == user.school_id,
            WritingTask.created_by == user.id,
        )
    )
    task = task_result.scalar_one_or_none()
    if task is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Writing task not found.", 404)
    class_row = await ensure_teacher_assigned_to_class(db, user, payload.class_id)

    existing_result = await db.execute(
        select(Assignment).where(
            Assignment.school_id == user.school_id,
            Assignment.task_id == task_id,
            Assignment.class_id == payload.class_id,
        )
    )
    assignment = existing_result.scalar_one_or_none()
    if assignment is None:
        assignment = Assignment(
            school_id=user.school_id,
            task_id=task_id,
            class_id=payload.class_id,
            assigned_by=user.id,
        )
        db.add(assignment)
        await write_audit_log(
            db,
            request,
            "WRITING_TASK_ASSIGNED",
            user,
            {"task_id": task_id, "class_id": payload.class_id},
        )
        await db.commit()

    return success_response(
        request,
        {
            "assignment": {
                "id": assignment.id,
                "task_id": task_id,
                "class_id": payload.class_id,
                "class_name": class_row.name,
            }
        },
    )


@router.get("/student/tasks")
async def list_student_tasks(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    profile_result = await db.execute(
        select(StudentProfile).where(
            StudentProfile.school_id == user.school_id,
            StudentProfile.user_id == user.id,
        )
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None or profile.current_class_id is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Student class profile not found.", 404)

    result = await db.execute(
        select(WritingTask, Class.name)
        .join(Assignment, Assignment.task_id == WritingTask.id)
        .join(Class, Class.id == Assignment.class_id)
        .options(selectinload(WritingTask.rubric))
        .where(
            WritingTask.school_id == user.school_id,
            WritingTask.status == "PUBLISHED",
            Assignment.school_id == user.school_id,
            Assignment.class_id == profile.current_class_id,
        )
        .order_by(WritingTask.due_at.asc().nulls_last(), WritingTask.title)
    )
    rows = list(result)
    task_ids = [task.id for task, _ in rows]
    drafts_by_task: dict[str, Draft] = {}
    submissions_by_task: dict[str, Submission] = {}
    reviews_by_submission: dict[str, TeacherReview] = {}
    if task_ids:
        draft_result = await db.execute(
            select(Draft).where(
                Draft.school_id == user.school_id,
                Draft.student_id == user.id,
                Draft.task_id.in_(task_ids),
            )
        )
        drafts_by_task = {draft.task_id: draft for draft in draft_result.scalars().all()}
        submission_result = await db.execute(
            select(Submission).where(
                Submission.school_id == user.school_id,
                Submission.student_id == user.id,
                Submission.task_id.in_(task_ids),
            )
        )
        submissions = list(submission_result.scalars().all())
        submissions_by_task = {submission.task_id: submission for submission in submissions}
        submission_ids = [submission.id for submission in submissions]
        if submission_ids:
            review_result = await db.execute(
                select(TeacherReview)
                .join(MarkingResult, MarkingResult.id == TeacherReview.marking_result_id)
                .where(
                    TeacherReview.school_id == user.school_id,
                    TeacherReview.submission_id.in_(submission_ids),
                    MarkingResult.school_id == user.school_id,
                )
            )
            reviews_by_submission = {
                review.submission_id: review for review in review_result.scalars().all()
            }

    tasks = [
        add_student_task_state(
            serialize_task(task, [class_name]),
            drafts_by_task.get(task.id),
            submissions_by_task.get(task.id),
            reviews_by_submission.get(submissions_by_task[task.id].id)
            if task.id in submissions_by_task
            else None,
        )
        for task, class_name in rows
    ]
    return success_response(request, {"tasks": tasks})
