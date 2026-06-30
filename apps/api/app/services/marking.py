from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AIUsageLog, MarkingResult, PostWritingExercise, Rubric, Submission, WritingTask
from app.services.llm import (
    LLMAdapter,
    LLMError,
    LLMGenerationRequest,
    build_ai_marking_messages,
    get_llm_adapter,
)

MAX_MARKING_ATTEMPTS = 3


def serialize_marking_result(row: MarkingResult | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "submission_id": row.submission_id,
        "task_id": row.task_id,
        "student_id": row.student_id,
        "status": row.status,
        "content_score": row.content_score,
        "language_score": row.language_score,
        "organisation_score": row.organisation_score,
        "total_score": row.total_score,
        "confidence_level": row.confidence_level,
        "content_feedback": row.content_feedback,
        "language_feedback": row.language_feedback,
        "organisation_feedback": row.organisation_feedback,
        "strengths": row.strengths,
        "weaknesses": row.weaknesses,
        "sentence_level_comments": row.sentence_level_comments,
        "recommended_exercises": row.recommended_exercises,
        "warning_flags": row.warning_flags,
        "model_metadata": row.model_metadata,
        "attempts": row.attempts,
        "last_error": row.last_error,
        "queued_at": row.queued_at.isoformat(),
        "marked_at": row.marked_at.isoformat() if row.marked_at else None,
    }


def create_marking_result_for_submission(submission: Submission) -> MarkingResult:
    return MarkingResult(
        school_id=submission.school_id,
        submission_id=submission.id,
        task_id=submission.task_id,
        student_id=submission.student_id,
        status="QUEUED",
        strengths=[],
        weaknesses=[],
        sentence_level_comments=[],
        recommended_exercises=[],
        warning_flags=[],
        model_metadata={},
        attempts=0,
    )


def apply_ai_payload(row: MarkingResult, payload: dict[str, Any]) -> None:
    row.content_score = payload["content_score"]
    row.language_score = payload["language_score"]
    row.organisation_score = payload["organisation_score"]
    row.total_score = payload["total_score"]
    row.confidence_level = payload["confidence_level"]
    row.content_feedback = payload["content_feedback"]
    row.language_feedback = payload["language_feedback"]
    row.organisation_feedback = payload["organisation_feedback"]
    row.strengths = payload["strengths"]
    row.weaknesses = payload["weaknesses"]
    row.sentence_level_comments = payload["sentence_level_comments"]
    row.recommended_exercises = payload["recommended_exercises"]
    row.warning_flags = payload["warning_flags"]
    row.model_metadata = payload["model_metadata"]
    row.status = "AI_MARKED"
    row.last_error = None
    row.marked_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)


async def create_exercises_for_marking_result(db: AsyncSession, row: MarkingResult) -> None:
    existing_result = await db.execute(
        select(PostWritingExercise.id).where(
            PostWritingExercise.school_id == row.school_id,
            PostWritingExercise.marking_result_id == row.id,
        )
    )
    if existing_result.first() is not None:
        return

    for exercise in row.recommended_exercises:
        db.add(
            PostWritingExercise(
                school_id=row.school_id,
                marking_result_id=row.id,
                submission_id=row.submission_id,
                student_id=row.student_id,
                title=str(exercise.get("title", "Post-writing exercise"))[:255],
                exercise_type=str(exercise.get("exercise_type", "revision"))[:64],
                focus_area=str(exercise.get("focus_area", "Writing"))[:128],
                prompt=str(exercise.get("prompt", "")),
                status="ASSIGNED",
            )
        )


async def process_marking_result(
    db: AsyncSession,
    row: MarkingResult,
    *,
    adapter: LLMAdapter | None = None,
    max_attempts: int = MAX_MARKING_ATTEMPTS,
) -> MarkingResult:
    result = await db.execute(
        select(Submission, WritingTask, Rubric)
        .join(WritingTask, WritingTask.id == Submission.task_id)
        .join(Rubric, Rubric.id == WritingTask.rubric_id)
        .options(selectinload(Rubric.dimensions))
        .where(
            Submission.id == row.submission_id,
            Submission.school_id == row.school_id,
            WritingTask.school_id == row.school_id,
            Rubric.school_id == row.school_id,
        )
    )
    context = result.one_or_none()
    if context is None:
        row.status = "AI_MARKING_FAILED"
        row.last_error = "Submission marking context not found."
        row.updated_at = datetime.now(UTC)
        return row

    submission, task, rubric = context
    dimensions = sorted(rubric.dimensions, key=lambda dimension: dimension.sort_order)
    rubric_summary = "; ".join(
        f"{dimension.name}: {dimension.min_score}-{dimension.max_score}. {dimension.descriptor}"
        for dimension in dimensions
    )
    adapter = adapter or get_llm_adapter()
    messages = build_ai_marking_messages(
        task_title=task.title,
        task_instruction=task.instruction,
        rubric_summary=rubric_summary,
        essay_text=submission.content_text,
        nlp_metrics={"word_count": submission.word_count, "mode": submission.mode},
    )

    while row.attempts < max_attempts and row.status != "AI_MARKED":
        row.attempts += 1
        row.status = "PROCESSING"
        try:
            response = await adapter.generate_json(LLMGenerationRequest(messages=messages))
            apply_ai_payload(row, response.json_data)
            await create_exercises_for_marking_result(db, row)
            db.add(
                AIUsageLog(
                    school_id=row.school_id,
                    marking_result_id=row.id,
                    provider=response.provider,
                    model=response.model,
                    operation="AI_MARKING",
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.total_tokens,
                    status="SUCCESS",
                )
            )
        except LLMError as exc:
            row.last_error = str(exc)
            row.status = "QUEUED" if row.attempts < max_attempts else "AI_MARKING_FAILED"
            row.updated_at = datetime.now(UTC)
            db.add(
                AIUsageLog(
                    school_id=row.school_id,
                    marking_result_id=row.id,
                    provider="unknown",
                    model="unknown",
                    operation="AI_MARKING",
                    status="FAILED",
                    error_message=str(exc),
                )
            )
    return row
