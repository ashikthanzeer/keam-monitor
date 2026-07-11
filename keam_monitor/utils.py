from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")


def now_ist() -> str:
    """Return the current timestamp in Indian Standard Time."""
    return (
        datetime.now(timezone.utc)
        .astimezone(IST_TIMEZONE)
        .strftime("%Y-%m-%d %H:%M:%S IST")
    )


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace while preserving line breaks."""
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def safe_text(value: Any) -> str:
    """Convert a value to a clean string for logging and display."""
    if value is None:
        return ""
    return str(value).strip()
