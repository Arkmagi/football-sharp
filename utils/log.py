import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path('data')
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger('footy')
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(LOG_DIR / 'footy.log', maxBytes=2_000_000, backupCount=3)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s - %(message)s')
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)

__all__ = ["logger"]