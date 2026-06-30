from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openauth_client_id: str = "english-ai-writing-web"
    openauth_client_secret: str = "change-me-in-local-env"
    openauth_issuer: str = "english-ai-writing-openauth"
    openauth_token_ttl_seconds: int = 3600
    openauth_signing_secret: str = "change-me-in-local-env"
    openauth_users_json: str = "[]"
    openauth_users_json_file: str | None = None


class AuthUser(BaseModel):
    email: str
    password_hash: str
    user_id: str = Field(alias="sub")
    school_id: str | None = None
    role: str
    status: str = "ACTIVE"


@dataclass(frozen=True)
class IdentityStore:
    users_by_email: dict[str, AuthUser]

    @classmethod
    def from_settings(cls, settings: Settings) -> "IdentityStore":
        try:
            if settings.openauth_users_json_file:
                with open(settings.openauth_users_json_file, encoding="utf-8") as handle:
                    raw_users = json.load(handle)
            else:
                raw_users = json.loads(settings.openauth_users_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OPENAUTH_USERS_JSON is not valid JSON.") from exc
        users = [AuthUser.model_validate(item) for item in raw_users]
        return cls({user.email.lower().strip(): user for user in users})

    def authenticate(self, email: str, password: str) -> AuthUser:
        user = self.users_by_email.get(email.lower().strip())
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        if user.status != "ACTIVE":
            raise HTTPException(status_code=403, detail="Account is not active.")
        return user


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hex = encoded_hash.split("$", 3)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Configured password hash is invalid.") from exc
    if algorithm != "pbkdf2_sha256":
        raise HTTPException(status_code=500, detail="Unsupported password hash algorithm.")
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    ).hex()
    return hmac.compare_digest(derived, expected_hex)


def sign_payload(payload: dict, settings: Settings) -> str:
    body = b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(
        settings.openauth_signing_secret.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{body}.{b64url_encode(signature)}"


def verify_token(token: str, settings: Settings) -> dict:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid bearer token.") from exc
    expected = hmac.new(
        settings.openauth_signing_secret.encode("utf-8"),
        body.encode("ascii"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(b64url_encode(expected), signature):
        raise HTTPException(status_code=401, detail="Invalid bearer token.")
    payload = json.loads(b64url_decode(body))
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=401, detail="Bearer token expired.")
    return payload


def get_settings() -> Settings:
    return Settings()


def get_identity_store(settings: Annotated[Settings, Depends(get_settings)]) -> IdentityStore:
    return IdentityStore.from_settings(settings)


app = FastAPI(title="English AI Writing OpenAuth Service", version="0.0.0")


@app.get("/health")
async def health() -> dict:
    return {"service": "auth", "status": "ok"}


@app.post("/oauth/token")
async def token(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[IdentityStore, Depends(get_identity_store)],
    grant_type: Annotated[str, Form()],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str, Form()],
    scope: Annotated[str, Form()] = "openid profile email",
) -> JSONResponse:
    if grant_type != "password":
        raise HTTPException(status_code=400, detail="Unsupported grant type.")
    if client_id != settings.openauth_client_id or not hmac.compare_digest(
        client_secret, settings.openauth_client_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid OAuth client.")

    user = store.authenticate(username, password)
    now = int(time.time())
    payload = {
        "iss": settings.openauth_issuer,
        "sub": user.user_id,
        "email": user.email,
        "school_id": user.school_id,
        "role": user.role,
        "iat": now,
        "exp": now + settings.openauth_token_ttl_seconds,
        "scope": scope,
        "client_id": client_id,
    }
    return JSONResponse(
        {
            "access_token": sign_payload(payload, settings),
            "token_type": "Bearer",
            "expires_in": settings.openauth_token_ttl_seconds,
            "scope": scope,
        },
        headers={"cache-control": "no-store", "pragma": "no-cache"},
    )


@app.get("/userinfo")
async def userinfo(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required.")
    payload = verify_token(authorization.removeprefix("Bearer ").strip(), settings)
    return {
        "sub": payload["sub"],
        "email": payload["email"],
        "school_id": payload.get("school_id"),
        "role": payload["role"],
    }
