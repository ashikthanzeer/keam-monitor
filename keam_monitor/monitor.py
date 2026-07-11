from __future__ import annotations

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import MonitorConfig
from .parser import ParsedPage, change_summary, compute_hash, normalize_html
from .storage import StateStore
from .telegram import TelegramClient, build_message
from .utils import now_ist
from utils.subscribers import load_subscribers

logger = logging.getLogger(__name__)


class MonitorService:
    """Main orchestration service for monitoring a set of web pages."""

    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.session = self._build_session()
        self.state_store = StateStore(config.state_file)
        self.telegram_client: TelegramClient | None = None
        if config.telegram_token and config.telegram_chat_id:
            self.telegram_client = TelegramClient(
                config.telegram_token,
                config.telegram_chat_id,
                self.session,
            )

    def _build_session(self) -> requests.Session:
        """Build an HTTP session with retry behavior and configured headers."""
        retry_strategy = Retry(
            total=self.config.retry_count,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"User-Agent": self.config.user_agent})
        return session

    def run(self) -> int:
        """Fetch every configured URL, detect changes, and notify if needed."""
        if not self.config.urls:
            logger.error("No URLs configured for monitoring")
            return 1

        notifications_sent = 0
        for url in self.config.urls:
            try:
                changed = self.check_url(url)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Monitoring failed for %s: %s", url, exc)
                continue
            if changed:
                notifications_sent += 1

        if notifications_sent == 0:
            logger.info("No changes detected; no notifications sent")
        return 0

    def check_url(self, url: str) -> bool:
        """Fetch a single URL and detect whether meaningful content changed."""
        logger.info("Checking %s", url)
        html = self.fetch_page(url)
        parsed = normalize_html(html, base_url=url)
        current_hash = compute_hash(parsed.canonical_json())
        previous_state = self.state_store.get(url)

        if previous_state is None:
            self._persist_state(url, parsed, current_hash)
            logger.info("Initialized baseline state for %s", url)
            return False

        if previous_state.get("hash") == current_hash:
            logger.info("No change detected for %s", url)
            return False

        summary = change_summary(previous_state, parsed)
        self._persist_state(url, parsed, current_hash)
        self._notify(url, summary)
        logger.info("Detected a change for %s", url)
        return True

    def fetch_page(self, url: str) -> str:
        """Fetch the webpage with timeout and retry behaviour."""
        try:
            response = self.session.get(url, timeout=self.config.request_timeout)
            response.raise_for_status()
            return response.text
        except requests.Timeout as exc:
            logger.error("Timed out while fetching %s", url)
            raise RuntimeError(f"Timed out fetching {url}") from exc
        except requests.ConnectionError as exc:
            logger.error("Connection error while fetching %s", url)
            raise RuntimeError(f"Connection failed for {url}") from exc
        except requests.HTTPError as exc:
            logger.error("HTTP error while fetching %s: %s", url, exc)
            raise RuntimeError(f"HTTP error fetching {url}") from exc
        except requests.RequestException as exc:
            logger.error("Request error while fetching %s: %s", url, exc)
            raise RuntimeError(f"Request failed for {url}") from exc

    def _notify(self, url: str, summary: str) -> None:
        """Notify all subscribers about a detected change."""
        if self.telegram_client is None:
            logger.warning("Telegram credentials are not configured; skipping notification")
            return

        subscribers = load_subscribers()
        if not subscribers:
            logger.info("No subscribers available; skipping notification")
            return

        message = build_message(url=url, summary=summary, timestamp=now_ist())
        for chat_id in subscribers:
            client = TelegramClient(self.config.telegram_token or "", str(chat_id), self.session)
            client.send_message(message)

    def _persist_state(self, url: str, parsed: ParsedPage, current_hash: str) -> None:
        """Persist the latest parsed state for one monitored URL."""
        previous_state = self.state_store.get(url)
        timestamp = now_ist()
        state = {
            "hash": current_hash,
            "content": parsed.text,
            "documents": [item.to_state() for item in parsed.documents],
            "notices": [item.to_state() for item in parsed.notices],
            "links": list(parsed.links),
            "pdfs": list(parsed.pdfs),
            "titles": list(parsed.titles),
            "last_checked": timestamp,
            "last_changed": previous_state.get("last_changed") if previous_state else timestamp,
        }
        if previous_state is None or previous_state.get("hash") != current_hash:
            state["last_changed"] = timestamp
        self.state_store.set(url, state)
        self.state_store.save()
