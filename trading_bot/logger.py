# ============================================================
#  Loglash Moduli
# ============================================================

import logging
import csv
import os
from datetime import datetime
from config import LOG_FILE, TRADE_LOG


def setup_logger():
    """Logger sozlash"""
    os.makedirs('logs', exist_ok=True)

    logger = logging.getLogger('TradingBot')
    logger.setLevel(logging.DEBUG)

    # Fayl handler
    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.DEBUG)

    # Terminal handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def log_trade(action, symbol, qty, price, sl, tp, reason=''):
    """Savdoni CSV ga yozish"""
    os.makedirs('logs', exist_ok=True)
    file_exists = os.path.isfile(TRADE_LOG)

    with open(TRADE_LOG, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                'Vaqt', 'Harakat', 'Aksiya', 'Miqdor',
                'Narx', 'Stop-Loss', 'Take-Profit', 'Sabab'
            ])
        writer.writerow([
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            action, symbol, qty, price, sl, tp, reason
        ])


# Global logger
logger = setup_logger()
