import logging
import signal
import time

from app import create_app
from app.config import CONFIG_FILE
from app.settings import Config

logger = logging.getLogger("oncall.scheduler")

_shutdown = False


def _handle_shutdown(signum, frame):
    """Handle container shutdown signals."""

    global _shutdown
    _shutdown = True

    logger.info(
        "scheduler shutdown requested",
        extra={"extra": {"signal": signum}},
    )

    try:
        from app.services.scheduler import stop_scheduler

        stop_scheduler()
    except Exception:
        logger.exception("failed to stop scheduler cleanly")


def main():
    """Start IncidentRelay scheduler as a standalone process."""

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    app = create_app()
    logger.info("starting scheduler")
    with app.app_context():
        from app.services.scheduler import start_scheduler

        start_scheduler()
        logger.info(
            "scheduler worker started",
            extra={
                "extra": {
                    "event_type": "scheduler",
                    "config_file": CONFIG_FILE,
                    "db_type": Config.DB_TYPE,
                    "db_name": Config.DB_NAME,
                    "log_file": Config.LOG_FILE,
                }
            },
        )

        while not _shutdown:
            time.sleep(1)

    logger.info("scheduler stopped")


if __name__ == "__main__":
    main()
