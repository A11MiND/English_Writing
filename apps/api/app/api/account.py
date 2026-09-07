from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import resolve_current_user, write_audit_log
from app.core.database import get_session
from app.core.responses import ApiException, ErrorCode, success_response
from app.models import User
from app.services.entitlements import features_for_school, school_for_user
from app.services.identity_provisioning import change_identity_password

router = APIRouter(prefix="/api", tags=["account"])


@router.get("/account/capabilities")
async def account_capabilities(
    request: Request,
    user: Annotated[User, Depends(resolve_current_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    school = await school_for_user(db, user.school_id)
    return success_response(
        request,
        {
            "plan_code": school.plan_code,
            "subscription_status": school.subscription_status,
            "subscription_renews_at": (
                school.subscription_renews_at.isoformat() if school.subscription_renews_at else None
            ),
            "features": features_for_school(school),
        },
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/account/password")
async def change_own_password(
    payload: ChangePasswordRequest,
    request: Request,
    user: Annotated[User, Depends(resolve_current_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    if payload.new_password == payload.current_password:
        raise ApiException(ErrorCode.VALIDATION_ERROR, "Choose a password you have not used here before.", 400)
    await change_identity_password(
        email=user.email,
        new_password=payload.new_password,
        current_password=payload.current_password,
    )
    await write_audit_log(db, request, "ACCOUNT_PASSWORD_CHANGED", user)
    await db.commit()
    return success_response(request, {"changed": True})
