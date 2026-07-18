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
