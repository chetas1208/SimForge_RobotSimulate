"""Centralized logging helpers."""

from __future__ import annotations

import logging
from pathlib import Path


def get_logger(name: str, log_file: str | Path | None = None, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file is not None:
        destination = Path(log_file)
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(destination)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger

