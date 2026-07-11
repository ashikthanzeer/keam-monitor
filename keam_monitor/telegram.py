from __future__ import annotations

import logging

import requests

from .utils import now_ist

logger = logging.getLogger(__name__)

TELEGRAM_MAX_MESSAGE_LENGTH = 4096
ALERT_ICON = "\U0001f6a8"


class TelegramClient:
    """Small Telegram client for sending Markdown-formatted alerts."""

    def __init__(self, token: str, chat_id: str, session: requests.Session) -> None:
        self.token = token
        self.chat_id = chat_id
        self.session = session

    def send_message(self, text: str) -> None:
        """Send a message, splitting it if needed for Telegram limits."""
        for chunk in split_message(text):
            self._send_chunk(chunk)

    def _send_chunk(self, text: str) -> None:
        """Send one Telegram message chunk."""
        try:
            response = self.session.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.error(
                "Telegram message failed",
                extra={"chat_id": self.chat_id, "error": str(exc)},
            )
            return

        logger.info("Telegram message sent", extra={"chat_id": self.chat_id})


def split_message(text: str, max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """Split a message into Telegram-safe chunks."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines():
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= max_length:
            current = candidate
            continue

        if current:
            chunks.append(current)
        if len(line) > max_length:
            chunks.extend(_split_long_line(line, max_length))
            current = ""
        else:
            current = line

    if current:
        chunks.append(current)
    return chunks


def _split_long_line(line: str, max_length: int) -> list[str]:
    """Split a single long line into fixed-size chunks."""
    return [line[index : index + max_length] for index in range(0, len(line), max_length)]


def build_message(url: str, summary: str, timestamp: str | None = None) -> str:
    """Build a formatted Telegram alert."""
    stamp = timestamp or now_ist()
    lines = [
        f"{ALERT_ICON} KEAM Website Updated",
        "",
        summary,
        "",
        "Checked:",
        stamp,
        "",
        "Website:",
        url,
    ]
    return "\n".join(lines)
