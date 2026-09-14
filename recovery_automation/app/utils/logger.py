"""
Centralized logging for Recovery & Automation.

Writes to console and logs/app.log with rotation-friendly append mode.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.utils.config import get_settings

_CONFIGURED = False


def _configure_root_logger() -> logging.Logger:
    global _CONFIGURED
    settings = get_settings()
    logger = logging.getLogger("recovery_automation")

    if _CONFIGURED:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    log_path = settings.log_file_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _CONFIGURED = True
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger under the recovery_automation namespace."""
    root = _configure_root_logger()
    if not name:
        return root
    return root.getChild(name)
