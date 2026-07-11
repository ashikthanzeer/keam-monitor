from __future__ import annotations

import logging
import os


def configure_logging(level_name: str | None = None) -> logging.Logger:
    """Configure structured application logging with timestamps."""
    raw_level = level_name or os.getenv("LOG_LEVEL", "INFO")
    level_value = getattr(logging, raw_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level_value,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    return logging.getLogger("keam_monitor")
