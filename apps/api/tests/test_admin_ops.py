from __future__ import annotations

from app.api.admin_ops import latest_error_category


class UsageRow:
    def __init__(self, error_message: str | None) -> None:
        self.error_message = error_message


def test_latest_ai_error_category_is_sanitized() -> None:
    assert latest_error_category(UsageRow("401 Unauthorized")) == "AUTHENTICATION"
    assert latest_error_category(UsageRow("request timeout")) == "TIMEOUT"
    assert latest_error_category(UsageRow("output did not match JSON schema")) == "VALIDATION"
    assert latest_error_category(UsageRow("HTTP 429 rate limited")) == "RATE_LIMIT"
    assert latest_error_category(UsageRow("provider unavailable")) == "PROVIDER_ERROR"
    assert latest_error_category(UsageRow(None)) is None
