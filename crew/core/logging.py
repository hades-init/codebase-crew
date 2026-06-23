import sys
import logging
from logging.handlers import RotatingFileHandler

from crew.core.config import settings


def setup_logging():
    level = logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG

    formatter = logging.Formatter(
        fmt="%(asctime)-20s %(levelname)-8s %(name)s -  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        settings.LOG_DIR.joinpath("app.log"), maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.handlers.clear()
    logger.setLevel(level)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.INFO)
    logging.getLogger("langsmith").setLevel(logging.WARNING)
