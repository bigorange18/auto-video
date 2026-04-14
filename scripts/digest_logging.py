from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path


def _resolve_log_file() -> Path:
    """Resolve daily log file path from env or default logs directory."""
    env_log_file = os.getenv("DIGEST_LOG_FILE", "").strip()
    if env_log_file:
        return Path(env_log_file)

    env_log_dir = os.getenv("DIGEST_LOG_DIR", "logs").strip() or "logs"
    today = datetime.now().strftime("%Y-%m-%d")
    return Path(env_log_dir) / f"digest-{today}.log"


def setup_logging() -> Path:
    """Configure root logging with both console and file handlers.

    Log format includes: date, level, filename, line number, and message.
    """
    level_name = os.getenv("DIGEST_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    log_file = _resolve_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Prevent duplicate handlers when this function is called multiple times.
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setLevel(level)
            handler.setFormatter(formatter)
        return log_file

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    return log_file
