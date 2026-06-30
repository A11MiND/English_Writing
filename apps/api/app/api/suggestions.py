from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.writing import student_task_context
from app.core.auth import Role, require_roles
from app.core.database import get_session
from app.core.responses import ApiException, ErrorCode, success_response
from app.models import User
from app.services.grammar import check_grammar_with_cache

router = APIRouter(prefix="/api", tags=["suggestions"])


class SuggestionCheckPayload(BaseModel):
    task_id: str = Field(min_length=36, max_length=36)
    text: str = Field(min_length=1, max_length=20_000)
    language: str = Field(default="en-US", min_length=2, max_length=16)
    check_mode: Literal["CHANGED", "FULL"] = "CHANGED"


@router.post("/suggestions/check")
async def check_suggestions(
    payload: SuggestionCheckPayload,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    _, task, _ = await student_task_context(db, user, payload.task_id)
    if task.mode != "PRACTICE":
        raise ApiException(
            ErrorCode.ACCESS_DENIED,
            "Real-time suggestions are available for Practice Mode only.",
            403,
        )

    suggestions, cached, service_status = await check_grammar_with_cache(
        payload.text,
        language=payload.language,
    )
    return success_response(
        request,
        {
            "suggestions": [suggestion.model_dump() for suggestion in suggestions],
            "cached": cached,
            "service_status": service_status,
            "check_mode": payload.check_mode,
        },
    )
