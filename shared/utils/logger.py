import os
import logging
from logging.handlers import RotatingFileHandler

LOGS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
os.makedirs(LOGS_DIR, exist_ok=True)

log_formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Root logger setup
root_logger = logging.getLogger("jobportal")
root_logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

# File handler
file_handler = RotatingFileHandler(
    os.path.join(LOGS_DIR, "app.log"),
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

def get_logger(service_name: str = "app") -> logging.Logger:
    return logging.getLogger(f"jobportal.{service_name}")
