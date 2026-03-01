import logging
import sys
import os

from .constants import DEFAULT_LOG_LEVEL, LOG_FORMAT


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[90m",
        logging.INFO: "\033[36m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str, use_color: bool):
        super().__init__(fmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        if self.use_color:
            color = self.COLORS.get(record.levelno, "")
            r = logging.makeLogRecord(record.__dict__.copy())
            r.levelname = f"{color}{record.levelname}{self.RESET}"
            return super().format(r)
        return super().format(record)


def setup_logger(
    name: str = "mail_client",
    log_level: str = DEFAULT_LOG_LEVEL,
    log_format: str = LOG_FORMAT
) -> logging.Logger:
    logger = logging.getLogger(name)
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    if logger.handlers:
        return logger
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    force_color = os.getenv("FORCE_COLOR") == "1"
    no_color = os.getenv("NO_COLOR") == "1"
    is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    use_color = (force_color or is_tty) and not no_color
    formatter = ColorFormatter(log_format, use_color)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger
