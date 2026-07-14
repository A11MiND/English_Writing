from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiException, ErrorCode
from app.models import School

FREE_FEATURES: Final[dict[str, bool]] = {
    "grammar_check": True,
    "ai_assist": True,
    "read_aloud": False,
    "image_generation": False,
    "ai_marking": False,
    "reports": False,
}

PRO_FEATURES: Final[dict[str, bool]] = {feature: True for feature in FREE_FEATURES}


def features_for_school(school: School) -> dict[str, bool]:
    if school.plan_code == "SCHOOL_PRO" and school.subscription_status == "ACTIVE":
        return PRO_FEATURES.copy()
    return FREE_FEATURES.copy()


async def school_for_user(db: AsyncSession, school_id: str | None) -> School:
    if not school_id:
        raise ApiException(ErrorCode.ACCESS_DENIED, "This account is not linked to a school.", 403)
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if school is None:
        raise ApiException(ErrorCode.NOT_FOUND, "School account not found.", 404)
    return school


def require_feature(school: School, feature: str) -> None:
    if not features_for_school(school).get(feature, False):
        raise ApiException(
            ErrorCode.ACCESS_DENIED,
            f"{feature.replace('_', ' ').title()} is included with School Pro.",
            403,
        )
