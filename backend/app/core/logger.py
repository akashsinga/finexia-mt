import logging
import sys
import os

def get_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Allow dynamic log level from env, fallback to DEBUG
        level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
        level = getattr(logging, level_str, logging.DEBUG)
        logger.setLevel(level)

        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S")

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)

        logger.addHandler(console_handler)

    return logger
