# ============================================================
#  Web Dashboard — Konfiguratsiya
# ============================================================

import os

class Config:
    SECRET_KEY       = os.environ.get('SECRET_KEY', 'ibkr-trading-secret-2024')
    DEBUG            = os.environ.get('DEBUG', 'True') == 'True'
    HOST             = os.environ.get('HOST', '0.0.0.0')
    PORT             = int(os.environ.get('PORT', 5000))

    # IBKR sozlamalari
    IBKR_HOST        = '127.0.0.1'
    IBKR_PORT        = 7497          # Paper: 7497 | Live: 7496
    IBKR_CLIENT_ID   = 2             # Bot 1 ishlatayotgan bo'lsa, bu 2

    # Trading sozlamalari
    ACCOUNT_SIZE     = 10000
    RISK_PERCENT     = 1.5
    REWARD_RATIO     = 2.0
    PARTIAL_CLOSE    = 50
    TRAILING_STOP    = 1.0
    MAX_POSITIONS    = 5
    MAX_DAILY_LOSS   = 3.0
    SCAN_INTERVAL    = 300

    # Log fayl joylashuvi (trading_bot papkasi)
    TRADE_LOG        = os.path.join(
        os.path.dirname(__file__),
        '..', 'trading_bot', 'logs', 'trades.csv'
    )
    BOT_LOG          = os.path.join(
        os.path.dirname(__file__),
        '..', 'trading_bot', 'logs', 'trading_bot.log'
    )
    # Demo ma'lumotlar (IBKR ulanmagan holda ko'rsatish uchun)
    DEMO_MODE        = True
