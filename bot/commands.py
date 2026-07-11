from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from utils.subscribers import load_subscribers

STATE_FILE = Path(__file__).resolve().parent.parent / "state.json"
DEFAULT_URL = "https://cee.kerala.gov.in/keam2026/allotlist"
logger = logging.getLogger(__name__)


def load_latest_state() -> dict[str, Any]:
    """Load the latest monitoring state from the repository JSON file."""
    if not STATE_FILE.exists():
        return {}

    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning(
            "State file contains invalid JSON",
            extra={"path": str(STATE_FILE), "error": str(exc)},
        )
        return {}
    except OSError as exc:
        logger.error(
            "Failed to read state file",
            extra={"path": str(STATE_FILE), "error": str(exc)},
        )
        return {}

    if isinstance(payload, dict):
        return payload
    logger.warning(
        "State file root must be a JSON object",
        extra={"path": str(STATE_FILE)},
    )
    return {}


def get_first_state_entry(state: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """Return the first valid URL state entry from the stored state."""
    for url, entry in state.items():
        if isinstance(entry, dict):
            return url, entry
    return None


def get_monitor_status() -> str:
    """Build a human-readable status message for the bot."""
    state = load_latest_state()
    state_entry = get_first_state_entry(state)
    latest_url, latest_entry = state_entry if state_entry else (DEFAULT_URL, None)

    last_checked = (
        latest_entry.get("last_checked", "Not available")
        if latest_entry
        else "Not available"
    )
    last_changed = (
        latest_entry.get("last_changed", "Not available")
        if latest_entry
        else "Not available"
    )
    subscriber_count = len(load_subscribers())

    return (
        "\U0001f7e2 KEAM Monitor\n\n"
        "Status:\nRunning\n\n"
        f"Website:\n{latest_url}\n\n"
        f"Subscribers:\n{subscriber_count}\n\n"
        f"Last Check:\n{last_checked}\n\n"
        f"Last Change:\n{last_changed}"
    )


def get_latest_update() -> str:
    """Return the latest stored change summary from the monitor state."""
    state = load_latest_state()
    state_entry = get_first_state_entry(state)
    latest_entry = state_entry[1] if state_entry else None

    if not latest_entry:
        return "No monitoring state has been captured yet."

    content = latest_entry.get("content", "")
    if isinstance(content, str) and content.strip():
        return content[:2000]
    return "No content available yet."
