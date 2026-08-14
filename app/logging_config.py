"""Structured logging setup for Marketing SEO Booster."""

from __future__ import annotations

import logging
import sys

from app.config_loader import app_env, log_format, log_level


def setup_logging() -> None:
    level = getattr(logging, log_level(), logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if log_format() == "json":
        try:
            from pythonjsonlogger import jsonlogger

            handler.setFormatter(
                jsonlogger.JsonFormatter(
                    "%(asctime)s %(levelname)s %(name)s %(message)s"
                )
            )
        except ImportError:
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
            )
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    if app_env() == "production":
        logging.getLogger("uvicorn.error").setLevel(logging.INFO)
