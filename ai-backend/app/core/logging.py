"""Logging com redação de dados sensíveis (LGPD)."""

from __future__ import annotations

import logging
import re
import sys

from .config import get_settings

_SENSITIVE = re.compile(
    r"(\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{15}\b|[\w.%-]+@[\w.-]+\.[a-z]{2,})",
    re.IGNORECASE,
)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _SENSITIVE.sub("[REDACTED]", record.msg)
        if record.args:
            record.args = tuple(
                _SENSITIVE.sub("[REDACTED]", str(arg)) for arg in record.args
            )
        return True


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    handler.addFilter(RedactingFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
