"""Application Constants."""

from __future__ import annotations

from typing import Any, Final

APP_LOG_LEVEL_REG_KEY: Final[str] = "sghi.mentorship-xls-forms.log_level"

APP_VERBOSITY_REG_KEY: Final[str] = "sghi.mentorship-xls-forms.cli.verbosity"

LOGGING_CONFIG_KEY: Final[str] = "LOGGING"

DEFAULT_CONFIG: Final[dict[str, Any]] = {
    LOGGING_CONFIG_KEY: {
        "version": 1,
        "formatters": {
            "simple": {
                "format": (
                    "%(asctime)s %(levelname)s %(name)s.%(funcName)s - "
                    "%(message)s"
                ),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "simple",
                "level": "DEBUG",
            },
        },
        "loggers": {
            "sghi": {"level": "WARNING", "handlers": ["console"]},
        },
    },
}
