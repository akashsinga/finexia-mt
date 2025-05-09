import logging
import sys
import os

# ANSI escape sequences for log level coloring
LOG_COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[41m",  # Red background
    "RESET": "\033[0m",  # Reset color
}


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        color = LOG_COLORS.get(levelname, "")
        reset = LOG_COLORS["RESET"]
        record.levelname = f"{color}{levelname}{reset}"
        record.name = f"{color}{record.name}{reset}"
        return super().format(record)


def get_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
        level = getattr(logging, level_str, logging.DEBUG)
        logger.setLevel(level)

        formatter = ColoredFormatter("[%(asctime)s] [%(levelname)s] %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S")

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)

        logger.addHandler(console_handler)

    return logger
