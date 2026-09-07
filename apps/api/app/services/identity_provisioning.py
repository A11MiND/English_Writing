import httpx

from app.core.config import get_settings
from app.core.responses import ApiException, ErrorCode


async def provision_identity(
    *,
    email: str,
    password: str,
    user_id: str,
    school_id: str,
    role: str,
) -> None:
    settings = get_settings()
    if not settings.openauth_register_url or not settings.openauth_client_secret:
        raise ApiException(ErrorCode.AUTH_REQUIRED, "Account provisioning is not configured.", 503)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.openauth_register_url,
                headers={"x-openauth-client-secret": settings.openauth_client_secret},
                json={
                    "email": email,
                    "password": password,
                    "user_id": user_id,
                    "school_id": school_id,
                    "role": role,
                },
            )
    except httpx.HTTPError as exc:
        raise ApiException(ErrorCode.AUTH_REQUIRED, "Account service is unavailable.", 503) from exc
    if response.status_code == 409:
        raise ApiException(ErrorCode.DUPLICATE_RECORD, "Email is already registered.", 409)
    if response.status_code >= 400:
        raise ApiException(ErrorCode.AUTH_REQUIRED, "Account could not be created.", 503)


async def change_identity_password(
    *,
    email: str,
    new_password: str,
    current_password: str | None,
) -> None:
    """Set an identity's password. Passing current_password makes the auth service verify it."""
    settings = get_settings()
    if not settings.openauth_register_url or not settings.openauth_client_secret:
        raise ApiException(ErrorCode.AUTH_REQUIRED, "Account provisioning is not configured.", 503)
    url = settings.openauth_register_url.rstrip("/") + "/password"
    body: dict[str, str] = {"email": email, "new_password": new_password}
    if current_password is not None:
        body["current_password"] = current_password
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                headers={"x-openauth-client-secret": settings.openauth_client_secret},
                json=body,
            )
    except httpx.HTTPError as exc:
        raise ApiException(ErrorCode.AUTH_REQUIRED, "Account service is unavailable.", 503) from exc
    if response.status_code == 401:
        raise ApiException(ErrorCode.VALIDATION_ERROR, "Current password is incorrect.", 400)
    if response.status_code == 404:
        raise ApiException(ErrorCode.NOT_FOUND, "No sign-in exists for that account yet.", 404)
    if response.status_code == 403:
        raise ApiException(ErrorCode.ACCESS_DENIED, "Account is not active.", 403)
    if response.status_code >= 400:
        raise ApiException(ErrorCode.AUTH_REQUIRED, "Password could not be changed.", 503)
