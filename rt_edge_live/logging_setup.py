"""Konsol log yapilandirmasi (ana + alt surecler)."""

from __future__ import annotations

import logging


def configure_logging(level: int) -> None:
    if logging.getLogger().handlers:
        logging.getLogger().setLevel(level)
        return
    fmt = "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")


def ensure_child_logging(level: int) -> None:
    if not logging.getLogger().handlers:
        configure_logging(level)
