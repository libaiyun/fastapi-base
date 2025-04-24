import logging
from typing import Any

from app.context import request_id_context
from app.config import config, APP_ENV
from app.config.models import AppEnv

_DEFAULT_FILE_HANDLER = {
    "filters": ["request_id"],
    "formatter": "simple",
    "class": "concurrent_log_handler.ConcurrentTimedRotatingFileHandler",
    "filename": config.log.log_dir / "app.log",
    "when": config.log.rotate_when,
    "interval": 1,
    "backupCount": config.log.backup_count,
    "encoding": "utf8",
    "delay": False,
}

LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "app.core.log.RequestIDFilter"}},
    "formatters": {
        "simple": {"format": "[%(asctime)s] [%(request_id)s] %(levelname)s %(message)s"},
        "verbose": {
            "format": "[%(asctime)s] [%(request_id)s] %(levelname)s %(pathname)s "
            "%(lineno)d %(funcName)s %(process)d %(thread)d "
            "\n \t [%(name)s] %(message)s \n",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
            "filters": ["request_id"],
        },
        "app": {
            **_DEFAULT_FILE_HANDLER,
            "formatter": "verbose",
        },
        "server": {
            **_DEFAULT_FILE_HANDLER,
            "filename": config.log.log_dir / "server.log",
        },
        "access": {
            **_DEFAULT_FILE_HANDLER,
            "filename": config.log.log_dir / "access.log",
        },
        "task": {
            **_DEFAULT_FILE_HANDLER,
            "filename": config.log.log_dir / "task.log",
        },
        "apscheduler": {
            **_DEFAULT_FILE_HANDLER,
            "filename": config.log.log_dir / "apscheduler.log",
        },
    },
    "loggers": {
        "": {"handlers": ["console"], "level": "INFO"},
        "app": {"handlers": ["app", "console"], "level": "INFO", "propagate": False},
        "app.config": {"handlers": ["app", "console"], "level": "INFO", "propagate": False},
        "app.task": {"handlers": ["task", "console"], "level": "INFO", "propagate": False},
        "uvicorn": {"handlers": ["server", "console"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["access", "console"], "level": "INFO", "propagate": False},
        "__main__": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apscheduler": {"handlers": ["apscheduler", "console"], "level": "INFO", "propagate": False},
    },
}

if APP_ENV == AppEnv.DEV:
    for _logger in LOGGING_CONFIG["loggers"]:
        LOGGING_CONFIG["loggers"][_logger]["handlers"] = ["console"]

if config.debug:
    for _logger in LOGGING_CONFIG["loggers"]:
        LOGGING_CONFIG["loggers"][_logger]["level"] = "DEBUG"


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_context.get("-")
        return True
