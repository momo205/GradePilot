from __future__ import annotations

from google.genai.errors import ClientError

from app.services.gemini_rate_limit import (
    gemini_client_error_is_daily_quota,
    is_gemini_rate_limit_client_error,
)


def test_gemini_client_error_daily_quota_detection() -> None:
    body = {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "message": "Quota exceeded for GenerateRequestsPerDayPerModel-FreeTier",
        }
    }
    err = ClientError(429, body, None)
    assert is_gemini_rate_limit_client_error(err)
    assert gemini_client_error_is_daily_quota(err) is True


def test_gemini_client_error_429_without_per_day_not_daily_flag() -> None:
    body = {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "message": "Please retry in 30s.",
        }
    }
    err = ClientError(429, body, None)
    assert is_gemini_rate_limit_client_error(err)
    assert gemini_client_error_is_daily_quota(err) is False
