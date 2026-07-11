from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_URL = "https://cee.kerala.gov.in/keam2026/allotlist"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_STATE_FILE = Path(__file__).resolve().parent.parent / "state.json"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonitorConfig:
    """Runtime configuration for the monitor service."""

    urls: tuple[str, ...]
    request_timeout: int = 20
    retry_count: int = 3
    poll_interval: int = 300
    telegram_token: str | None = None
    telegram_chat_id: str | None = None
    user_agent: str = DEFAULT_USER_AGENT
    state_file: Path = field(default_factory=lambda: DEFAULT_STATE_FILE)

    @classmethod
    def from_environment(cls) -> "MonitorConfig":
        """Build configuration from defaults and supported environment variables."""
        raw_urls = os.getenv("MONITOR_URLS", "").strip()
        if raw_urls:
            urls = tuple(url.strip() for url in raw_urls.split(",") if url.strip())
        else:
            url = os.getenv("MONITOR_URL", DEFAULT_URL).strip() or DEFAULT_URL
            urls = (url,)

        return cls(
            urls=urls,
            request_timeout=_int_from_environment("REQUEST_TIMEOUT", 20),
            retry_count=_int_from_environment("RETRY_COUNT", 3),
            poll_interval=_int_from_environment("POLL_INTERVAL", 300),
            telegram_token=os.getenv('TELEGRAM_BOT_TOKEN'),
            telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID'),
            user_agent=(
                os.getenv("USER_AGENT", DEFAULT_USER_AGENT).strip()
                or DEFAULT_USER_AGENT
            ),
            state_file=Path(os.getenv("STATE_FILE", str(DEFAULT_STATE_FILE))),
        )


def _int_from_environment(name: str, default: int) -> int:
    """Read an integer environment value, falling back when it is invalid."""
    raw_value = os.getenv(name, str(default)).strip()
    try:
        return int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid integer configuration value; using default",
            extra={"name": name, "value": raw_value, "default": default},
        )
        return default
