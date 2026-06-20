import sys
import json
import logging
from typing import Literal

# This module provides logging utilities for the RAG packages. It sets up a base logger and provides a JSON formatter for structured logging. The `enable_package_logging` function allows configuring the logging level and format (pretty or JSON) for the package.

BASE_LOGGER_NAME = "rag_packages"

logger = logging.getLogger(BASE_LOGGER_NAME)
logger.addHandler(logging.NullHandler())

DEFAULT_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "process": record.process,
            "thread": record.thread,
        }

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in DEFAULT_LOG_RECORD_FIELDS
        }
        if extras:
            log["context"] = extras

        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)

        return json.dumps(log)


def enable_package_logging(
    level=logging.INFO, formatter: Literal["pretty", "json"] = "pretty"
):
    logger = logging.getLogger(BASE_LOGGER_NAME)

    # prevent duplicate logging handlers
    if any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        return  # Logging is already configured

    log_formatters = {
        "json": JsonFormatter(),
        "pretty": logging.Formatter(
            "%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s"
        ),
    }

    # StreamHandler for logging to console (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatters[formatter])

    logger.setLevel(level)
    logger.addHandler(stream_handler)
    logger.propagate = False  # prevent double logging if root logger is configured; log goes rag_packages -> root logger -> ... -> console
