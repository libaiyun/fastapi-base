from typing import Any

from config import config, Environment

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
            "filename": config.log.server_logfile,
        },
        "access": {
            **_DEFAULT_FILE_HANDLER,
            "filename": config.log.access_logfile,
        },
        "scheduler_async": {
            **_DEFAULT_FILE_HANDLER,
            "filename": config.log.scheduler_async_logfile,
        },
        "scheduler": {
            **_DEFAULT_FILE_HANDLER,
            "filename": config.log.scheduler_logfile,
        },
    },
    "loggers": {
        "app": {"handlers": ["app"], "level": "INFO"},
        "uvicorn": {"handlers": ["server"], "level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        "scheduler_async": {"handlers": ["scheduler_async"], "level": "INFO"},
        "scheduler": {"handlers": ["scheduler"], "level": "INFO"},
    },
}

if config.environment == Environment.DEVELOPMENT:
    for _logger in LOGGING_CONFIG["loggers"]:
        LOGGING_CONFIG["loggers"][_logger]["handlers"] = ["console"]
