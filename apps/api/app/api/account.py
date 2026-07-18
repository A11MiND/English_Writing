from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import resolve_current_user
from app.core.database import get_session
from app.core.responses import success_response
from app.models import User
from app.services.entitlements import features_for_school, school_for_user

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
