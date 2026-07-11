from __future__ import annotations

import json

from bot import commands


def test_status_uses_first_state_entry(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "https://example.com/old": {
                    "content": "Old content",
                    "last_checked": "2026-07-09 20:00:00 IST",
                    "last_changed": "2026-07-09 20:00:00 IST",
                },
                "https://example.com/new": {
                    "content": "New content",
                    "last_checked": "2026-07-09 23:00:00 IST",
                    "last_changed": "2026-07-09 22:00:00 IST",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(commands, "STATE_FILE", state_file)
    monkeypatch.setattr(commands, "load_subscribers", lambda: [101, 202])

    status = commands.get_monitor_status()

    assert "KEAM Monitor" in status
    assert "https://example.com/old" in status
    assert "Subscribers:\n2" in status
    assert "Last Check:\n2026-07-09 20:00:00 IST" in status


def test_latest_update_uses_first_state_entry(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "https://example.com/old": {
                    "content": "Old content",
                    "last_checked": "2026-07-09 20:00:00 IST",
                },
                "https://example.com/new": {
                    "content": "New content",
                    "last_checked": "2026-07-09 23:00:00 IST",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(commands, "STATE_FILE", state_file)

    assert commands.get_latest_update() == "Old content"


def test_status_falls_back_when_state_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(commands, "STATE_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(commands, "load_subscribers", lambda: [])

    status = commands.get_monitor_status()

    assert commands.DEFAULT_URL in status
    assert "Subscribers:\n0" in status
    assert "Last Check:\nNot available" in status
