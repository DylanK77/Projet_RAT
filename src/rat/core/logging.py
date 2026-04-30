from __future__ import annotations

import logging
import logging.config
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LogSettings:
    name: str
    level: str = "INFO"
    log_dir: Path = Path("data") / "logs"
    filename: str = "rat.log"
    max_bytes: int = 2_000_000
    backup_count: int = 5


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def setup_logging(settings: LogSettings) -> logging.Logger:
    _ensure_dir(settings.log_dir)
    log_path = settings.log_dir / settings.filename

    level = os.environ.get("RAT_LOG_LEVEL", settings.level).upper()

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": level,
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "level": level,
                    "filename": str(log_path),
                    "maxBytes": settings.max_bytes,
                    "backupCount": settings.backup_count,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                settings.name: {
                    "handlers": ["console", "file"],
                    "level": level,
                    "propagate": False,
                }
            },
        }
    )

    return logging.getLogger(settings.name)
