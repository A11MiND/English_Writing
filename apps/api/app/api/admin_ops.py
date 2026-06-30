from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AccountStatus, Role, require_roles, write_audit_log
from app.core.config import get_settings
from app.core.database import get_session
from app.core.responses import ApiException, ErrorCode, success_response
from app.models import AIUsageLog, User, utc_now
from app.services.llm import LLMConfigurationError, get_provider_preset

router = APIRouter(prefix="/api", tags=["admin-ops"])


class UpdateUserStatusRequest(BaseModel):
    status: AccountStatus
    reason: str | None = Field(default=None, max_length=500)


def latest_error_category(row: AIUsageLog | None) -> str | None:
    if row is None or not row.error_message:
        return None
    message = row.error_message.lower()
    if "api_key" in message or "401" in message or "403" in message or "unauthorized" in message:
        return "AUTHENTICATION"
    if "timeout" in message:
        return "TIMEOUT"
    if "schema" in message or "json" in message:
        return "VALIDATION"
    if "rate" in message or "429" in message:
        return "RATE_LIMIT"
    return "PROVIDER_ERROR"


@router.get("/admin/ai/status")
async def get_admin_ai_status(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    settings = get_settings()
    configured = bool(settings.llm_api_key)
    config_error: str | None = None
    try:
        preset = get_provider_preset(settings.llm_provider)
        model = settings.llm_model or preset.default_model
        base_url_configured = bool(settings.llm_base_url or preset.base_url)
        configured = configured and base_url_configured
    except LLMConfigurationError as exc:
        preset = None
        model = settings.llm_model
        base_url_configured = False
        configured = False
        config_error = str(exc)

    latest_result = await db.execute(
        select(AIUsageLog)
        .where(
            AIUsageLog.school_id == user.school_id,
            AIUsageLog.operation == "AI_MARKING",
        )
        .order_by(desc(AIUsageLog.created_at))
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()

    return success_response(
        request,
        {
            "provider": settings.llm_provider,
            "provider_display_name": preset.display_name if preset else settings.llm_provider,
            "model": model,
            "configured": configured,
            "api_key_configured": bool(settings.llm_api_key),
            "base_url_configured": base_url_configured,
            "last_call_status": latest.status if latest else None,
            "last_error_category": latest_error_category(latest) or config_error,
            "last_called_at": latest.created_at.isoformat() if latest else None,
        },
    )


@router.patch("/admin/users/{user_id}/status")
async def update_admin_user_status(
    user_id: str,
    payload: UpdateUserStatusRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    if user_id == user.id and payload.status != AccountStatus.ACTIVE:
        raise ApiException(ErrorCode.VALIDATION_ERROR, "Administrators cannot suspend or archive themselves.", 422)

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.school_id == user.school_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise ApiException(ErrorCode.NOT_FOUND, "User account not found.", 404)
    if account.role == Role.SYSTEM_ADMIN and user.role != Role.SYSTEM_ADMIN:
        raise ApiException(ErrorCode.ACCESS_DENIED, "Only system admins can modify system admin accounts.", 403)

    old_status = account.status
    account.status = payload.status
    account.updated_at = utc_now()
    await write_audit_log(
        db,
        request,
        "ACCOUNT_STATUS_UPDATED",
        user,
        {
            "target_user_id": account.id,
            "target_role": account.role,
            "old_status": old_status,
            "new_status": payload.status,
            "reason": payload.reason,
        },
    )
    await db.commit()
    await db.refresh(account)

    return success_response(
        request,
        {
            "user": {
                "id": account.id,
                "email": account.email,
                "display_name": account.display_name,
                "role": account.role,
                "status": account.status,
            }
        },
    )
