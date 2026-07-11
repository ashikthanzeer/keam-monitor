from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateStore:
    """Persist monitor state as JSON for one or more URLs."""

    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        """Load state data from disk, returning an empty state on failure."""
        if not self.state_file.exists():
            return {}

        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning(
                "State file contains invalid JSON",
                extra={"path": str(self.state_file), "error": str(exc)},
            )
            return {}
        except OSError as exc:
            logger.error(
                "Failed to read state file",
                extra={"path": str(self.state_file), "error": str(exc)},
            )
            return {}

        if not isinstance(payload, dict):
            logger.warning(
                "State file root must be a JSON object",
                extra={"path": str(self.state_file)},
            )
            return {}

        return {
            str(url): entry
            for url, entry in payload.items()
            if isinstance(entry, dict)
        }

    def save(self) -> None:
        """Write the current state data to disk."""
        try:
            self.state_file.write_text(
                json.dumps(self._data, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.error(
                "Failed to write state file",
                extra={"path": str(self.state_file), "error": str(exc)},
            )

    def get(self, url: str) -> dict[str, Any] | None:
        """Return the stored state for a URL, if present."""
        state = self._data.get(url)
        if state is None:
            return None
        return dict(state)

    def set(self, url: str, state: dict[str, Any]) -> None:
        """Store state for a URL in memory."""
        self._data[url] = dict(state)

    def clear(self) -> None:
        """Remove all stored state and persist the empty state."""
        self._data = {}
        self.save()
