"""Rate limit configuration tests."""

from app.config import get_settings
from app.middleware.rate_limit import get_default_limit, get_search_limit


def test_rate_limit_values_come_from_settings() -> None:
    settings = get_settings()
    assert get_default_limit() == f"{settings.rate_limit_default_per_minute}/minute"
    assert get_search_limit() == f"{settings.rate_limit_search_per_minute}/minute"
