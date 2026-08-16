"""Minimal structured logging setup."""

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure process logging without logging private content."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named application logger."""

    return logging.getLogger(name)

