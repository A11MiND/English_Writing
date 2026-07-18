import pytest

from app.core.responses import ApiException
from app.models import School
from app.services.entitlements import features_for_school, require_feature


def test_school_pro_inherits_all_product_capabilities() -> None:
    school = School(name="Demo School", code="DEMO", plan_code="SCHOOL_PRO", subscription_status="ACTIVE")

    assert all(features_for_school(school).values())


def test_free_school_keeps_writing_basics_and_locks_costly_media() -> None:
    school = School(name="Demo School", code="DEMO", plan_code="FREE", subscription_status="ACTIVE")
    features = features_for_school(school)

    assert features["grammar_check"] is True
    assert features["ai_assist"] is True
    assert features["read_aloud"] is False
    assert features["image_generation"] is False

    with pytest.raises(ApiException) as exc_info:
        require_feature(school, "read_aloud")
    assert exc_info.value.status_code == 403
