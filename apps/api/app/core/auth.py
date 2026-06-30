from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated

import httpx
from fastapi import Cookie, Depends, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import AsyncSessionLocal
from app.core.responses import ApiException, ErrorCode
from app.models import AuditLog, User, UserSession


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class Role(StrEnum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


class AuthenticatedUser(BaseModel):
    id: str
    email: str
    display_name: str
    role: Role
    school_id: str | None
    status: AccountStatus


@dataclass(frozen=True)
class OpenAuthSubject:
    user_id: str
    school_id: str | None
    role: Role


class OpenAuthAdapter:
    async def authenticate(self, email: str, password: str) -> OpenAuthSubject:
        raise NotImplementedError


class OpenAuthHTTPAdapter(OpenAuthAdapter):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def authenticate(self, email: str, password: str) -> OpenAuthSubject:
        self._ensure_configured()
        token_payload = await self._exchange_password(email, password)
        claims = await self._load_userinfo(token_payload)
        return self._subject_from_claims(claims)

    def _ensure_configured(self) -> None:
        missing = [
            name
            for name, value in {
                "OPENAUTH_TOKEN_URL": self.settings.openauth_token_url,
                "OPENAUTH_USERINFO_URL": self.settings.openauth_userinfo_url,
                "OPENAUTH_CLIENT_ID": self.settings.openauth_client_id,
                "OPENAUTH_CLIENT_SECRET": self.settings.openauth_client_secret,
            }.items()
            if not value
        ]
        if missing:
            raise ApiException(
                ErrorCode.AUTH_REQUIRED,
                f"OpenAuth is not configured: {', '.join(missing)}.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    async def _exchange_password(self, email: str, password: str) -> dict:
        assert self.settings.openauth_token_url
        assert self.settings.openauth_client_id
        assert self.settings.openauth_client_secret
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.settings.openauth_token_url,
                    data={
                        "grant_type": "password",
                        "username": email,
                        "password": password,
                        "client_id": self.settings.openauth_client_id,
                        "client_secret": self.settings.openauth_client_secret,
                        "scope": self.settings.openauth_scope,
                    },
                    headers={"accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise ApiException(
                ErrorCode.AUTH_REQUIRED,
                "OpenAuth token exchange failed.",
                status.HTTP_401_UNAUTHORIZED,
            ) from exc
        if response.status_code >= 400:
            raise ApiException(
                ErrorCode.AUTH_REQUIRED,
                "Invalid email or password.",
                status.HTTP_401_UNAUTHORIZED,
            )
        return response.json()

    async def _load_userinfo(self, token_payload: dict) -> dict:
        assert self.settings.openauth_userinfo_url
        access_token = token_payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise ApiException(
                ErrorCode.AUTH_REQUIRED,
                "OpenAuth token response did not include an access token.",
                status.HTTP_401_UNAUTHORIZED,
            )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.settings.openauth_userinfo_url,
                    headers={"authorization": f"Bearer {access_token}", "accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise ApiException(
                ErrorCode.AUTH_REQUIRED,
                "OpenAuth userinfo request failed.",
                status.HTTP_401_UNAUTHORIZED,
            ) from exc
        if response.status_code >= 400:
            raise ApiException(
                ErrorCode.AUTH_REQUIRED,
                "OpenAuth userinfo request was rejected.",
                status.HTTP_401_UNAUTHORIZED,
            )
        return response.json()

    def _subject_from_claims(self, claims: dict) -> OpenAuthSubject:
        user_id = claims.get(self.settings.openauth_user_id_claim)
        school_id = claims.get(self.settings.openauth_school_id_claim)
        role = claims.get(self.settings.openauth_role_claim)
        if not isinstance(user_id, str) or not user_id:
            raise ApiException(ErrorCode.AUTH_REQUIRED, "OpenAuth subject claim is missing.", 401)
        if school_id is not None and not isinstance(school_id, str):
            raise ApiException(ErrorCode.ACCESS_DENIED, "OpenAuth school claim is invalid.", 403)
        try:
            parsed_role = Role(str(role))
        except ValueError as exc:
            raise ApiException(ErrorCode.ACCESS_DENIED, "OpenAuth role claim is invalid.", 403) from exc
        return OpenAuthSubject(user_id=user_id, school_id=school_id, role=parsed_role)


def get_openauth_adapter() -> OpenAuthAdapter:
    return OpenAuthHTTPAdapter(get_settings())


def session_hash(session_token: str) -> str:
    return sha256(session_token.encode("utf-8")).hexdigest()


def user_to_payload(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=Role(user.role),
        school_id=user.school_id,
        status=AccountStatus(user.status),
    )


async def write_audit_log(
    session: AsyncSession,
    request: Request,
    action: str,
    user: User | None,
    metadata: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            school_id=user.school_id if user else None,
            actor_user_id=user.id if user else None,
            actor_role=user.role if user else None,
            action=action,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            event_metadata=metadata or {},
        )
    )


async def get_user_by_subject(session: AsyncSession, subject: OpenAuthSubject) -> User:
    result = await session.execute(select(User).where(User.id == subject.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ApiException(ErrorCode.AUTH_REQUIRED, "Authenticated user is not registered.", 401)
    if user.role != subject.role:
        raise ApiException(ErrorCode.ACCESS_DENIED, "Authenticated role does not match profile.", 403)
    if user.school_id != subject.school_id:
        raise ApiException(ErrorCode.ACCESS_DENIED, "Authenticated school does not match profile.", 403)
    if user.status != AccountStatus.ACTIVE:
        raise ApiException(ErrorCode.ACCESS_DENIED, "Account is not active.", 403)
    return user


async def create_session(
    db: AsyncSession, response: Response, request: Request, user: User
) -> AuthenticatedUser:
    settings = get_settings()
    token = token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    db.add(UserSession(user_id=user.id, session_hash=session_hash(token), expires_at=expires_at))
    user.last_login_at = datetime.now(UTC)
    await write_audit_log(db, request, "AUTH_LOGIN", user)
    await db.commit()

    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_ttl_hours * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    return user_to_payload(user)


async def resolve_current_user(
    request: Request,
    session_cookie: Annotated[str | None, Cookie(alias="eaiwp_session")] = None,
) -> User:
    if not session_cookie:
        raise ApiException(ErrorCode.AUTH_REQUIRED, "Authentication required.", 401)

    async with AsyncSessionLocal() as db:
        statement: Select[tuple[UserSession]] = select(UserSession).where(
            UserSession.session_hash == session_hash(session_cookie)
        )
        result = await db.execute(statement)
        session_row = result.scalar_one_or_none()
        if session_row is None or session_row.invalidated_at is not None:
            raise ApiException(ErrorCode.AUTH_REQUIRED, "Authentication required.", 401)
        expires_at = session_row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            raise ApiException(ErrorCode.AUTH_REQUIRED, "Session expired.", 401)

        user_result = await db.execute(select(User).where(User.id == session_row.user_id))
        user = user_result.scalar_one_or_none()
        if user is None or user.status != AccountStatus.ACTIVE:
            raise ApiException(ErrorCode.ACCESS_DENIED, "Account is not active.", 403)
        request.state.current_user = user
        request.state.current_session_id = session_row.id
        return user


def require_roles(*allowed_roles: Role):
    async def dependency(user: Annotated[User, Depends(resolve_current_user)]) -> User:
        if Role(user.role) not in allowed_roles:
            raise ApiException(ErrorCode.ACCESS_DENIED, "Access denied for this role.", 403)
        return user

    return dependency
