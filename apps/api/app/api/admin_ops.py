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
from app.models import AIProviderSetting, AIUsageLog, User, utc_now
from app.services.ai_settings import get_school_ai_setting, resolve_ai_settings
from app.services.identity_provisioning import change_identity_password
from app.services.llm import (
    LLMError,
    LLMGenerationRequest,
    LLMMessage,
    build_llm_adapter,
    get_provider_preset,
)

router = APIRouter(prefix="/api", tags=["admin-ops"])


class UpdateUserStatusRequest(BaseModel):
    status: AccountStatus
    reason: str | None = Field(default=None, max_length=500)


class UpdateAISettingsRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    model: str | None = Field(default=None, max_length=128)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=4000)
    clear_api_key: bool = False
    timeout_seconds: int = Field(default=30, ge=1, le=120)


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


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
    config_error: str | None = None
    try:
        resolved = await resolve_ai_settings(db, user.school_id)
    except LLMError as exc:
        resolved = None
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
            "provider": resolved.provider if resolved else get_settings().llm_provider,
            "provider_display_name": resolved.provider_display_name if resolved else get_settings().llm_provider,
            "model": resolved.model if resolved else get_settings().llm_model,
            "configured": resolved.configured if resolved else False,
            "api_key_configured": resolved.api_key_configured if resolved else False,
            "base_url_configured": resolved.base_url_configured if resolved else False,
            "source": resolved.source if resolved else "invalid",
            "masked_api_key": resolved.masked_api_key if resolved else None,
            "last_call_status": latest.status if latest else None,
            "last_error_category": latest_error_category(latest) or config_error,
            "last_called_at": latest.created_at.isoformat() if latest else None,
        },
    )


@router.get("/admin/ai/settings")
async def get_admin_ai_settings(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    resolved = await resolve_ai_settings(db, user.school_id)
    return success_response(
        request,
        {
            "provider": resolved.provider,
            "provider_display_name": resolved.provider_display_name,
            "model": resolved.model,
            "base_url": resolved.base_url,
            "timeout_seconds": resolved.timeout_seconds,
            "configured": resolved.configured,
            "api_key_configured": resolved.api_key_configured,
            "masked_api_key": resolved.masked_api_key,
            "source": resolved.source,
        },
    )


@router.patch("/admin/ai/settings")
async def update_admin_ai_settings(
    payload: UpdateAISettingsRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    if user.school_id is None:
        raise ApiException(ErrorCode.VALIDATION_ERROR, "Admin account is not assigned to a school.", 422)
    preset = get_provider_preset(payload.provider)
    row = await get_school_ai_setting(db, user.school_id)
    if row is None:
        row = AIProviderSetting(
            school_id=user.school_id,
            provider=preset.id,
            timeout_seconds=payload.timeout_seconds,
            updated_by=user.id,
        )
        db.add(row)

    row.provider = preset.id
    row.model = clean_optional(payload.model)
    row.base_url = clean_optional(payload.base_url)
    row.timeout_seconds = payload.timeout_seconds
    row.updated_by = user.id
    row.updated_at = utc_now()
    if payload.clear_api_key:
        row.api_key_secret = None
    elif payload.api_key is not None:
        row.api_key_secret = clean_optional(payload.api_key)

    await write_audit_log(
        db,
        request,
        "AI_SETTINGS_UPDATED",
        user,
        {
            "provider": row.provider,
            "model": row.model,
            "base_url_configured": bool(row.base_url or preset.base_url),
            "api_key_configured": bool(row.api_key_secret),
        },
    )
    await db.commit()
    resolved = await resolve_ai_settings(db, user.school_id)
    return success_response(
        request,
        {
            "provider": resolved.provider,
            "provider_display_name": resolved.provider_display_name,
            "model": resolved.model,
            "base_url": resolved.base_url,
            "timeout_seconds": resolved.timeout_seconds,
            "configured": resolved.configured,
            "api_key_configured": resolved.api_key_configured,
            "masked_api_key": resolved.masked_api_key,
            "source": resolved.source,
        },
    )


@router.post("/admin/ai/test")
async def test_admin_ai_settings(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    resolved = await resolve_ai_settings(db, user.school_id)
    try:
        adapter = build_llm_adapter(
            provider=resolved.provider,
            model=resolved.model,
            base_url=resolved.base_url,
            api_key=resolved.api_key,
            timeout_seconds=resolved.timeout_seconds,
        )
        response = await adapter.generate_json(
            LLMGenerationRequest(
                response_schema_name="connection_test",
                max_tokens=120,
                messages=[
                    LLMMessage(
                        role="system",
                        content="Return only a JSON object. No markdown.",
                    ),
                    LLMMessage(
                        role="user",
                        content='Return {"ok": true, "purpose": "connection_test"}.',
                    ),
                ],
            )
        )
        ok = response.json_data.get("ok") is True
        db.add(
            AIUsageLog(
                school_id=user.school_id,
                provider=response.provider,
                model=response.model,
                operation="AI_CONNECTION_TEST",
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.total_tokens,
                status="SUCCESS" if ok else "FAILED",
                error_message=None if ok else "Provider returned JSON but did not confirm ok=true.",
            )
        )
        await db.commit()
        return success_response(
            request,
            {
                "ok": ok,
                "provider": response.provider,
                "model": response.model,
                "message": "Connection test succeeded." if ok else "Provider response was not accepted.",
            },
        )
    except LLMError as exc:
        db.add(
            AIUsageLog(
                school_id=user.school_id,
                provider=resolved.provider,
                model=resolved.model,
                operation="AI_CONNECTION_TEST",
                status="FAILED",
                error_message=str(exc),
            )
        )
        await db.commit()
        raise ApiException(ErrorCode.VALIDATION_ERROR, f"AI connection test failed: {exc}", 422) from exc


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


class ResetUserPasswordRequest(BaseModel):
    temporary_password: str = Field(min_length=8, max_length=128)


@router.post("/admin/users/{user_id}/password")
async def reset_admin_user_password(
    user_id: str,
    payload: ResetUserPasswordRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    result = await db.execute(
        select(User).where(User.id == user_id, User.school_id == user.school_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise ApiException(ErrorCode.NOT_FOUND, "User account not found.", 404)
    if account.role == Role.SYSTEM_ADMIN and user.role != Role.SYSTEM_ADMIN:
        raise ApiException(ErrorCode.ACCESS_DENIED, "Only system admins can modify system admin accounts.", 403)

    await change_identity_password(
        email=account.email,
        new_password=payload.temporary_password,
        current_password=None,
    )
    await write_audit_log(
        db,
        request,
        "ACCOUNT_PASSWORD_RESET",
        user,
        {"target_user_id": account.id, "target_role": account.role},
    )
    await db.commit()
    return success_response(request, {"reset": True, "email": account.email})
