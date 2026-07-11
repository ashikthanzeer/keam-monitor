from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

SUBSCRIBERS_FILE = Path(__file__).resolve().parent.parent / "data" / "subscribers.json"

logger = logging.getLogger(__name__)


def _normalize_chat_id(chat_id: Any) -> int | None:
    """Convert a chat ID to an integer, returning None for invalid values."""
    try:
        value = str(chat_id).strip()
        return int(value) if value else None
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid Telegram chat ID", extra={"chat_id": chat_id})
        return None


def load_subscribers(path: Path | None = None) -> list[int]:
    """Load subscriber chat IDs from disk."""
    target = path or SUBSCRIBERS_FILE
    if not target.exists():
        return []

    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning(
            "Subscriber file contains invalid JSON",
            extra={"path": str(target), "error": str(exc)},
        )
        return []
    except OSError as exc:
        logger.error(
            "Failed to read subscriber file",
            extra={"path": str(target), "error": str(exc)},
        )
        return []

    subscribers = payload.get("subscribers", []) if isinstance(payload, dict) else []
    if not isinstance(subscribers, list):
        logger.warning(
            "Subscriber file has an invalid subscribers value",
            extra={"path": str(target)},
        )
        return []

    normalized = [_normalize_chat_id(chat_id) for chat_id in subscribers]
    return [chat_id for chat_id in normalized if chat_id is not None]


def save_subscribers(subscribers: list[int], path: Path | None = None) -> None:
    """Persist subscriber chat IDs to disk."""
    target = path or SUBSCRIBERS_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = [_normalize_chat_id(chat_id) for chat_id in subscribers]
    payload = {
        "subscribers": sorted({chat_id for chat_id in normalized if chat_id is not None})
    }

    try:
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.error(
            "Failed to write subscriber file",
            extra={"path": str(target), "error": str(exc)},
        )


def add_subscriber(chat_id: int | str, path: Path | None = None) -> bool:
    """Add a subscriber if it is not already present."""
    subscribers = load_subscribers(path)
    normalized = _normalize_chat_id(chat_id)
    if normalized is None:
        return False

    if normalized in subscribers:
        return False

    subscribers.append(normalized)
    save_subscribers(subscribers, path)
    return True


def remove_subscriber(chat_id: int | str, path: Path | None = None) -> bool:
    """Remove a subscriber if it exists."""
    subscribers = load_subscribers(path)
    normalized = _normalize_chat_id(chat_id)
    if normalized is None:
        return False

    if normalized not in subscribers:
        return False

    updated = [value for value in subscribers if value != normalized]
    save_subscribers(updated, path)
    return True


def is_subscribed(chat_id: int | str, path: Path | None = None) -> bool:
    """Check whether a chat ID is already subscribed."""
    normalized = _normalize_chat_id(chat_id)
    if normalized is None:
        return False
    return normalized in load_subscribers(path)
