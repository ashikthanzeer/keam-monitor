from __future__ import annotations

import hashlib
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import unified_diff
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, Comment
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_URL = "https://cee.kerala.gov.in/keam2026/allotlist"
REPO_ROOT = Path(__file__).resolve().parent
HASH_FILE = REPO_ROOT / "last_hash.txt"
CONTENT_FILE = REPO_ROOT / "last_content.txt"
REQUEST_TIMEOUT_SECONDS = 20
MAX_RETRIES = 3
BACKOFF_SECONDS = 2
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")


@dataclass(frozen=True)
class MonitorConfig:
    url: str
    hash_file: Path
    content_file: Path


def build_session() -> requests.Session:
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_SECONDS,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def get_monitor_urls() -> list[str]:
    raw_urls = os.getenv("MONITOR_URLS")
    if raw_urls:
        return [url.strip() for url in raw_urls.split(",") if url.strip()]

    return [os.getenv("MONITOR_URL", DEFAULT_URL).strip()]


def get_state_paths(url: str) -> Tuple[Path, Path]:
    if url == DEFAULT_URL:
        return HASH_FILE, CONTENT_FILE

    suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return REPO_ROOT / f"last_hash_{suffix}.txt", REPO_ROOT / f"last_content_{suffix}.txt"


def normalize_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "noscript", "svg", "iframe", "meta", "link", "header", "footer", "nav", "form", "input", "button", "select", "option", "aside"]):
        tag.decompose()

    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()

    visible_text = soup.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in visible_text.splitlines() if line.strip()]
    normalized = "\n".join(lines)
    return normalized


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_previous_state(hash_file: Path, content_file: Path) -> Tuple[Optional[str], Optional[str]]:
    previous_hash = None
    previous_content = None

    if hash_file.exists():
        previous_hash = hash_file.read_text(encoding="utf-8").strip() or None
    if content_file.exists():
        previous_content = content_file.read_text(encoding="utf-8").strip() or None

    return previous_hash, previous_content


def save_state(content: str, hash_value: str, hash_file: Path, content_file: Path) -> None:
    hash_file.write_text(hash_value, encoding="utf-8")
    content_file.write_text(content, encoding="utf-8")


def get_current_time_ist() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %Z")


def fetch_page(session: requests.Session, url: str) -> str:
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text
    except requests.HTTPError as exc:
        logger.error("HTTP error while fetching %s: %s", url, exc)
        raise
    except requests.RequestException as exc:
        logger.error("Network error while fetching %s: %s", url, exc)
        raise RuntimeError(f"Failed to fetch {url}") from exc


def summarize_changes(previous_content: Optional[str], current_content: str) -> Tuple[str, List[str]]:
    if previous_content is None:
        return "Initial baseline captured; no notification sent.", []

    previous_lines = previous_content.splitlines()
    current_lines = current_content.splitlines()
    diff_lines = list(
        unified_diff(
            previous_lines,
            current_lines,
            fromfile="previous",
            tofile="current",
            n=2,
        )
    )

    changed_lines: List[str] = []
    for line in diff_lines:
        if line.startswith(("+", "-")) and not line.startswith(("++", "--")):
            changed_lines.append(line[1:].strip())

    if not changed_lines:
        return "Content changed, but the diff did not produce visible line edits.", []

    summary = f"Detected {len(changed_lines)} changed lines."
    return summary, changed_lines[:8]


def build_telegram_message(url: str, summary: str, changed_lines: List[str], timestamp: str) -> str:
    message: list[str] = [
        "🚨 KEAM allotment page changed",
        f"Time: {timestamp}",
        f"URL: {url}",
        f"Summary: {summary}",
    ]

    if changed_lines:
        message.append("Changed lines:")
        message.extend(f"- {line}" for line in changed_lines)

    message.append(f"Open: {url}")
    return "\n".join(message)


def send_telegram_notification(session: requests.Session, token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        raise ValueError("Telegram bot token and chat id must be set in environment variables.")

    response = session.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    logger.info("Telegram notification sent.")


def monitor_url(config: MonitorConfig, session: requests.Session, token: str, chat_id: str) -> bool:
    logger.info("Checking %s", config.url)

    html = fetch_page(session, config.url)
    normalized_content = normalize_content(html)
    current_hash = compute_hash(normalized_content)

    previous_hash, previous_content = load_previous_state(config.hash_file, config.content_file)
    if previous_hash == current_hash:
        logger.info("No change detected for %s.", config.url)
        return False

    if previous_hash is None:
        logger.info("Baseline state saved for %s. No notification will be sent on first run.", config.url)
        save_state(normalized_content, current_hash, config.hash_file, config.content_file)
        return False

    summary, changed_lines = summarize_changes(previous_content, normalized_content)
    timestamp = get_current_time_ist()
    message_text = build_telegram_message(config.url, summary, changed_lines, timestamp)

    send_telegram_notification(session, token, chat_id, message_text)
    save_state(normalized_content, current_hash, config.hash_file, config.content_file)
    logger.info("Updated state saved for %s.", config.url)
    return True


def main() -> int:
    urls = get_monitor_urls()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "8733253525:AAGRxMEVRH4aozvbu7W4KeE2GPpq_NGwvJ4").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "7857522005").strip()

    if not urls:
        logger.error("No monitor URLs configured. Set MONITOR_URL or MONITOR_URLS.")
        return 1

    if not token or not chat_id:
        logger.error("Missing Telegram credentials. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return 1

    session = build_session()
    notifications_sent = 0

    for url in urls:
        hash_file, content_file = get_state_paths(url)
        config = MonitorConfig(url=url, hash_file=hash_file, content_file=content_file)

        try:
            if monitor_url(config, session, token, chat_id):
                notifications_sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to monitor %s: %s", url, exc)
            return 1

    if notifications_sent == 0:
        logger.info("No notifications sent.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
