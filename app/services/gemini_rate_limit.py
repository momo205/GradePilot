"""Parse retry hints from google.genai ClientError (e.g. 429 RESOURCE_EXHAUSTED)."""

from __future__ import annotations

import json
import re
from typing import Any

from google.api_core.exceptions import ResourceExhausted
from google.genai.errors import ClientError

_RETRY_IN_TEXT = re.compile(
    r"Please retry in\s+([0-9]+(?:\.[0-9]+)?)\s*s",
    re.IGNORECASE,
)
_RETRY_DELAY_VALUE = re.compile(
    r"^([0-9]+(?:\.[0-9]+)?)\s*s\s*$",
    re.IGNORECASE,
)


def parse_retry_after_seconds_from_text(msg: str) -> int | None:
    m = _RETRY_IN_TEXT.search(msg or "")
    if not m:
        return None
    try:
        return max(1, int(float(m.group(1)) + 0.999))
    except ValueError:
        return None


def retry_after_seconds_from_genai_client_error(error: ClientError) -> int | None:
    for chunk in (error.message, str(error)):
        if isinstance(chunk, str) and chunk:
            got = parse_retry_after_seconds_from_text(chunk)
            if got is not None:
                return got
    stack: list[Any] = [error.details]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            rd = cur.get("retryDelay")
            if isinstance(rd, str):
                m = _RETRY_DELAY_VALUE.match(rd.strip())
                if m:
                    try:
                        return max(1, int(float(m.group(1)) + 0.999))
                    except ValueError:
                        pass
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def is_gemini_rate_limit_client_error(error: ClientError) -> bool:
    if error.code == 429:
        return True
    st = (error.status or "") or ""
    return "RESOURCE_EXHAUSTED" in st.upper()


def _scan_blob_for_daily_quota(blob: str) -> bool:
    compact = blob.lower().replace("_", "").replace(" ", "")
    if "perday" in compact:
        return True
    if "requestsperday" in compact:
        return True
    if "perdayperproject" in compact:
        return True
    return False


def gemini_client_error_is_daily_quota(error: ClientError) -> bool:
    """True when 429 is tied to daily free-tier caps (retrying immediately won't help)."""
    if not is_gemini_rate_limit_client_error(error):
        return False
    parts: list[str] = [str(error.message or ""), str(error)]
    try:
        parts.append(json.dumps(error.details, default=str))
    except Exception:
        parts.append(repr(error.details))
    return _scan_blob_for_daily_quota(" ".join(parts))


def resource_exhausted_is_likely_daily_quota(exc: ResourceExhausted) -> bool:
    return _scan_blob_for_daily_quota(str(exc))
