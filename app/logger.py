#!/usr/bin/env python3

"""Centralized logging configuration."""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging(level: int | None = None) -> None:
    """Configure root logging only once."""
    if getattr(configure_logging, "_configured", False):
        return
    logging.basicConfig(
        level=level or logging.INFO,
        format=LOG_FORMAT,
    )
    configure_logging._configured = True  # type: ignore[attr-defined]


configure_logging()

# Expose module-level logger helper
logger = logging.getLogger("biyoves")
