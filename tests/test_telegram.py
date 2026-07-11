from __future__ import annotations

from keam_monitor.telegram import build_message, split_message


def test_build_message_contains_summary_and_url() -> None:
    message = build_message("https://example.com", "New PDF Added")
    assert "KEAM Website Updated" in message
    assert "New PDF Added" in message
    assert "https://example.com" in message


def test_split_message_breaks_large_messages() -> None:
    long_text = "x" * 5000
    chunks = split_message(long_text)
    assert len(chunks) > 1
    assert all(len(chunk) <= 4096 for chunk in chunks)
