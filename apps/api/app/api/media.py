from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.tasks import teacher_task_or_404
from app.api.writing import student_task_context
from app.core.auth import Role, require_roles, resolve_current_user, write_audit_log
from app.core.config import get_settings
from app.core.database import get_session
from app.core.responses import ApiException, ErrorCode, success_response
from app.models import AIUsageLog, User, WritingTask
from app.services.entitlements import require_feature, school_for_user
from app.services.minimax_media import MiniMaxMediaClient, MiniMaxMediaError

router = APIRouter(prefix="/api", tags=["media"])


class SpeechRequest(BaseModel):
    task_id: str = Field(min_length=36, max_length=36)
    context: Literal["PROMPT", "WRITING"]
    text: str = Field(default="", max_length=10_000)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()


async def accessible_task(db: AsyncSession, user: User, task_id: str) -> WritingTask:
    if user.role == Role.STUDENT:
        _, task, _ = await student_task_context(db, user, task_id)
        return task
    if user.role == Role.TEACHER:
        return await teacher_task_or_404(db, user, task_id)
    result = await db.execute(
        select(WritingTask).where(
            WritingTask.id == task_id,
            WritingTask.school_id == user.school_id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise ApiException(ErrorCode.NOT_FOUND, "Writing task not found.", 404)
    return task


@router.post("/media/speech")
async def read_aloud(
    payload: SpeechRequest,
    request: Request,
    user: Annotated[User, Depends(resolve_current_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    school = await school_for_user(db, user.school_id)
    require_feature(school, "read_aloud")
    task = await accessible_task(db, user, payload.task_id)
    text = task.instruction if payload.context == "PROMPT" else payload.text
    if not text:
        raise ApiException(ErrorCode.VALIDATION_ERROR, "There is no text to read aloud.", 422)

    client = MiniMaxMediaClient()
    try:
        asset = await client.synthesize_speech(text)
    except MiniMaxMediaError as exc:
        db.add(
            AIUsageLog(
                school_id=school.id,
                provider="minimax",
                model=get_settings().minimax_speech_model,
                operation="READ_ALOUD",
                prompt_tokens=len(text),
                status="FAILED",
                error_message=str(exc)[:1000],
            )
        )
        await db.commit()
        raise ApiException(ErrorCode.AI_MARKING_FAILED, str(exc), 503) from exc

    db.add(
        AIUsageLog(
            school_id=school.id,
            provider="minimax",
            model=asset.model,
            operation="READ_ALOUD",
            prompt_tokens=len(text),
            status="SUCCESS",
        )
    )
    await write_audit_log(
        db,
        request,
        "TEXT_READ_ALOUD",
        user,
        {"task_id": task.id, "context": payload.context, "character_count": len(text)},
    )
    await db.commit()
    return Response(
        content=asset.content,
        media_type=asset.mime_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.post("/teacher/tasks/{task_id}/image")
async def generate_task_image(
    task_id: str,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    school = await school_for_user(db, user.school_id)
    require_feature(school, "image_generation")
    task = await teacher_task_or_404(db, user, task_id)
    prompt = (
        "A warm, polished storybook illustration for Hong Kong primary school pupils aged 9 to 12. "
        "Professional educational editorial style, gentle colour, expressive but not childish, landscape composition. "
        "No words, letters, logos, brand marks, watermarks, or identifiable real children. "
        f"Writing topic: {task.title}. Prompt context: {task.instruction}"
    )

    client = MiniMaxMediaClient()
    try:
        asset = await client.generate_image(prompt)
    except MiniMaxMediaError as exc:
        db.add(
            AIUsageLog(
                school_id=school.id,
                provider="minimax",
                model=get_settings().minimax_image_model,
                operation="TASK_IMAGE_GENERATION",
                status="FAILED",
                error_message=str(exc)[:1000],
            )
        )
        await db.commit()
        raise ApiException(ErrorCode.AI_MARKING_FAILED, str(exc), 503) from exc

    root = Path(get_settings().media_storage_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"task-{task.id}.jpg"
    target.write_bytes(asset.content)
    task.image_path = str(target)
    task.image_mime_type = asset.mime_type
    db.add(
        AIUsageLog(
            school_id=school.id,
            provider="minimax",
            model=asset.model,
            operation="TASK_IMAGE_GENERATION",
            status="SUCCESS",
        )
    )
    await write_audit_log(db, request, "TASK_IMAGE_GENERATED", user, {"task_id": task.id})
    await db.commit()
    return success_response(request, {"image_url": f"/api/tasks/{task.id}/image"})


@router.get("/tasks/{task_id}/image")
async def get_task_image(
    task_id: str,
    user: Annotated[User, Depends(resolve_current_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> FileResponse:
    task = await accessible_task(db, user, task_id)
    if not task.image_path:
        raise ApiException(ErrorCode.NOT_FOUND, "Task image not found.", 404)
    root = Path(get_settings().media_storage_dir).resolve()
    image_path = Path(task.image_path).resolve()
    if image_path.parent != root or not image_path.is_file():
        raise ApiException(ErrorCode.NOT_FOUND, "Task image not found.", 404)
    return FileResponse(
        image_path,
        media_type=task.image_mime_type or "image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )
