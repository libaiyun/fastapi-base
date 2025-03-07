from typing import Any

from config import config, APP_ENV
from config.models import AppEnv

_DEFAULT_FILE_HANDLER = {
    "formatter": "simple",
    "class": "concurrent_log_handler.ConcurrentTimedRotatingFileHandler",
    "filename": config.log.app_logfile,
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
        "simple": {"format": "%(levelname)s [%(asctime)s] [%(name)s] %(message)s"},
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
            "filename": config.log.server_logfile,
        },
        "access": {
            **_DEFAULT_FILE_HANDLER,
            "filename": config.log.access_logfile,
        },
        "task": {
            **_DEFAULT_FILE_HANDLER,
            "filename": config.log.task_logfile,
        },
    },
    "loggers": {
        "app": {
            "handlers": [
                "app",
            ],
            "level": "INFO",
        },
        "config": {"handlers": ["app"], "level": "INFO"},
        "app.task": {
            "handlers": [
                "task",
            ],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn": {"handlers": ["server"], "level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        "__main__": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

if APP_ENV == AppEnv.DEV:
    for _logger in LOGGING_CONFIG["loggers"]:
        LOGGING_CONFIG["loggers"][_logger]["handlers"] = ["console"]
