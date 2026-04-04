import logging
import sys
from logging.handlers import RotatingFileHandler

# Configure basic logging with log rotation (5MB per file, 3 backups)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            "bot.log",
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding='utf-8'
        )
    ]
)

def get_logger(name):
    return logging.getLogger(name)
