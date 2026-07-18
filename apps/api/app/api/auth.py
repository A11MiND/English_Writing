from typing import Annotated
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    AuthenticatedUser,
    AccountStatus,
    OpenAuthAdapter,
    Role,
    create_session,
    get_openauth_adapter,
    get_user_by_subject,
    require_roles,
    resolve_current_user,
    session_hash,
    user_to_payload,
    write_audit_log,
)
from app.core.config import get_settings
from app.core.database import get_session
from app.core.responses import success_response
from app.models import User, UserSession

router = APIRouter(prefix="/api", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Valid email is required.")
        return normalized


@router.post("/auth/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    adapter: Annotated[OpenAuthAdapter, Depends(get_openauth_adapter)],
) -> dict:
    subject = await adapter.authenticate(str(payload.email), payload.password)
    user = await get_user_by_subject(db, subject)
    auth_user = await create_session(db, response, request, user)
    return success_response(request, {"user": auth_user.model_dump()})


@router.post("/auth/logout")
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(resolve_current_user)],
) -> dict:
    session_result = await db.execute(
        select(UserSession).where(UserSession.id == request.state.current_session_id)
    )
    session_row = session_result.scalar_one()
    session_row.invalidated_at = datetime.now(UTC)
    await write_audit_log(db, request, "AUTH_LOGOUT", user)
    await db.commit()
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return success_response(request, {"logged_out": True})


@router.get("/auth/session")
async def session_probe(request: Request, db: Annotated[AsyncSession, Depends(get_session)]) -> dict:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        return success_response(request, {"user": None})

    session_result = await db.execute(
        select(UserSession).where(UserSession.session_hash == session_hash(token))
    )
    session_row = session_result.scalar_one_or_none()
    if session_row is None or session_row.invalidated_at is not None:
        return success_response(request, {"user": None})

    expires_at = session_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        return success_response(request, {"user": None})

    user_result = await db.execute(select(User).where(User.id == session_row.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or user.status != AccountStatus.ACTIVE:
        return success_response(request, {"user": None})
    return success_response(request, {"user": user_to_payload(user).model_dump()})


@router.get("/auth/me")
async def me(request: Request, user: Annotated[User, Depends(resolve_current_user)]) -> dict:
    auth_user: AuthenticatedUser = user_to_payload(user)
    return success_response(request, {"user": auth_user.model_dump()})


@router.get("/protected/admin")
async def admin_only(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN))],
) -> dict:
    return success_response(request, {"role": user.role, "scope": "admin"})


@router.get("/protected/teacher")
async def teacher_only(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.TEACHER))],
) -> dict:
    return success_response(request, {"role": user.role, "scope": "teacher"})


@router.get("/protected/student")
async def student_only(
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
) -> dict:
    return success_response(request, {"role": user.role, "scope": "student"})
