import logging
import logging.config
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s %(module)s:%(lineno)d — %(message)s"

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": LOG_FORMAT,
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "level": "INFO",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["console", "file"], "level": "INFO"},
        "uvicorn.error": {"handlers": ["console", "file"], "level": "INFO"},
        "uvicorn.access": {"handlers": ["console", "file"], "level": "INFO"},
        "app": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("app")


def setup_logging():
    """Configure application logging."""
    logging.config.dictConfig(LOG_CONFIG)
