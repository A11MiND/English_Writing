from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AIUsageLog, MarkingResult, PostWritingExercise, Rubric, Submission, WritingTask
from app.services.ai_settings import get_school_llm_adapter
from app.services.llm import (
    LLMAdapter,
    LLMError,
    LLMGenerationRequest,
    build_ai_marking_messages,
)

MAX_MARKING_ATTEMPTS = 3

def rubric_score_limits(dimensions: list[Any]) -> dict[str, dict[str, int]]:
    """Score bounds for every dimension the school put on this rubric, keyed by name."""
    limits: dict[str, dict[str, int]] = {}
    for dimension in sorted(dimensions, key=lambda item: item.sort_order):
        limits[str(dimension.name).strip()] = {
            "min_score": int(dimension.min_score),
            "max_score": int(dimension.max_score),
        }
    if not limits:
        raise ValueError("Rubric has no dimensions to mark against.")
    return limits


def rubric_total_score(limits: dict[str, dict[str, int]]) -> int:
    return sum(limit["max_score"] for limit in limits.values())


def normalize_ai_marking_payload(
    payload: dict[str, Any], dimensions: list[Any]
) -> dict[str, Any]:
    """Clamp provider scores to the task rubric and make the total authoritative."""
    normalized = dict(payload)
    limits = rubric_score_limits(dimensions)
    by_name = {name.casefold(): name for name in limits}
    changes: dict[str, dict[str, int]] = {}

    provided = {
        str(entry.get("name", "")).strip().casefold(): entry
        for entry in (normalized.get("dimension_scores") or [])
    }
    missing = [name for name in limits if name.casefold() not in provided]
    if missing:
        raise ValueError(f"AI marking did not score: {', '.join(missing)}.")

    scored: list[dict[str, Any]] = []
    for canonical_name, limit in limits.items():
        entry = provided[canonical_name.casefold()]
        original = int(entry.get("score", 0))
        bounded = max(limit["min_score"], min(limit["max_score"], original))
        if bounded != original:
            changes[canonical_name] = {"provider": original, "normalized": bounded}
        scored.append(
            {
                "name": canonical_name,
                "score": bounded,
                "max_score": limit["max_score"],
                "feedback": str(entry.get("feedback", "")).strip(),
            }
        )

    # Anything the provider scored that the rubric does not define is dropped rather
    # than persisted, so a rubric edit cannot leave orphan scores behind.
    extra = [by_name.get(key, key) for key in provided if key not in {n.casefold() for n in limits}]

    normalized["dimension_scores"] = scored
    provider_total = int(normalized.get("total_score", 0))
    calculated_total = sum(int(item["score"]) for item in scored)
    normalized["total_score"] = calculated_total
    if provider_total != calculated_total:
        changes["total_score"] = {"provider": provider_total, "normalized": calculated_total}

    metadata = dict(normalized.get("model_metadata") or {})
    metadata["rubric_score_scale"] = {name: dict(limit) for name, limit in limits.items()}
    metadata["rubric_total_score"] = rubric_total_score(limits)
    if changes:
        metadata["score_normalization"] = changes
    if extra:
        metadata["ignored_dimensions"] = extra
    normalized["model_metadata"] = metadata
    return normalized


def serialize_marking_result(row: MarkingResult | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "submission_id": row.submission_id,
        "task_id": row.task_id,
        "student_id": row.student_id,
        "status": row.status,
        "dimension_scores": row.dimension_scores,
        "total_score": row.total_score,
        "confidence_level": row.confidence_level,
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
        dimension_scores=[],
        model_metadata={},
        attempts=0,
    )


def apply_ai_payload(row: MarkingResult, payload: dict[str, Any]) -> None:
    row.dimension_scores = payload["dimension_scores"]
    row.total_score = payload["total_score"]
    row.confidence_level = payload["confidence_level"]
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
    adapter = adapter or await get_school_llm_adapter(db, row.school_id)
    messages = build_ai_marking_messages(
        task_title=task.title,
        task_instruction=task.instruction,
        rubric_summary=rubric_summary,
        essay_text=submission.content_text,
        dimension_names=[str(dimension.name).strip() for dimension in dimensions],
        nlp_metrics={"word_count": submission.word_count, "mode": submission.mode},
    )

    while row.attempts < max_attempts and row.status != "AI_MARKED":
        row.attempts += 1
        row.status = "PROCESSING"
        try:
            response = await adapter.generate_json(LLMGenerationRequest(messages=messages))
            normalized_payload = normalize_ai_marking_payload(response.json_data, dimensions)
            apply_ai_payload(row, normalized_payload)
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
