from typing import Any

from config import config, APP_ENV
from config.models import AppEnv

_DEFAULT_FILE_HANDLER = {
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
    "formatters": {
        "simple": {"format": "%(levelname)s [%(asctime)s] %(message)s"},
        "verbose": {
            "format": "%(levelname)s [%(asctime)s] %(pathname)s "
            "%(lineno)d %(funcName)s %(process)d %(thread)d "
            "\n \t [%(name)s] %(message)s \n",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
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
    },
    "loggers": {
        "app": {"handlers": ["app", "console"], "level": "INFO"},
        "config": {"handlers": ["app", "console"], "level": "INFO"},
        "app.task": {"handlers": ["task", "console"], "level": "INFO", "propagate": False},
        "uvicorn": {"handlers": ["server", "console"], "level": "INFO"},
        "uvicorn.access": {"handlers": ["access", "console"], "level": "INFO", "propagate": False},
        "__main__": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

if APP_ENV == AppEnv.DEV:
    for _logger in LOGGING_CONFIG["loggers"]:
        LOGGING_CONFIG["loggers"][_logger]["handlers"] = ["console"]
