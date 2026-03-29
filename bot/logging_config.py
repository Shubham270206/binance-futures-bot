"""
Logging configuration for the Binance Futures Trading Bot.
Sets up dual-output logging: structured file logs + clean console output.
"""

import logging
import logging.handlers
import os
from pathlib import Path


LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

LOG_FORMAT_FILE = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
LOG_FORMAT_CONSOLE = "%(levelname)-8s | %(message)s"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure root logger with:
      - Rotating file handler (logs/trading_bot.log, max 5 MB, 3 backups)
      - Console handler (cleaner format, WARNING+ by default for less noise)

    Returns the root 'trading_bot' logger.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)  # capture everything; handlers filter

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    # --- File handler (rotating) ---
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(LOG_FORMAT_FILE, datefmt=DATE_FORMAT)
    )

    # --- Console handler ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(
        logging.Formatter(LOG_FORMAT_CONSOLE)
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logging initialised. Log file: %s", LOG_FILE)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'trading_bot' namespace."""
    return logging.getLogger(f"trading_bot.{name}")
