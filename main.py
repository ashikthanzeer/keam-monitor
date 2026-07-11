from __future__ import annotations

import logging
import sys

from keam_monitor.config import MonitorConfig
from keam_monitor.logger import configure_logging
from keam_monitor.monitor import MonitorService

logger = logging.getLogger(__name__)


def main() -> int:
    """Run the KEAM monitor command-line entrypoint."""
    configure_logging()
    config = MonitorConfig.from_environment()

    if not config.telegram_token or not config.telegram_chat_id:
        logger.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        return 1

    service = MonitorService(config)
    return service.run()


if __name__ == "__main__":
    sys.exit(main())
