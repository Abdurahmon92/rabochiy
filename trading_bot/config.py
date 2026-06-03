# ============================================================
#  IBKR Algoritmik Trading Bot — Konfiguratsiya
# ============================================================

# --- IBKR Ulanish Sozlamalari ---
IBKR_HOST = '127.0.0.1'       # TWS yoki IB Gateway manzili
IBKR_PORT = 7497               # TWS paper trading: 7497 | Live: 7496 | Gateway: 4002
IBKR_CLIENT_ID = 1

# --- Hisob Sozlamalari ---
ACCOUNT_SIZE = 10000           # Depozit miqdori (USD) — o'zingiznikini kiriting
RISK_PERCENT = 1.5             # Bir savdodagi risk (1% dan 2% gacha, default 1.5%)
REWARD_RATIO = 2.0             # Risk/Reward nisbati (1:2)
PARTIAL_CLOSE_PERCENT = 50     # 1:1 ga yetganda necha % yopish (50%)

# --- Trailing Stop Sozlamalari ---
TRAILING_STOP_PERCENT = 1.0    # Trailing stop masofasi (narxdan %)

# --- Finviz Skaner Filtrlari ---
FINVIZ_FILTERS = {
    'Exchange': 'NASDAQ,NYSE',         # Birjalar
    'Price':    'sh_price_o5',         # Narx > $5
    'Volume':   'sh_avgvol_o500',      # O\'rtacha volume > 500K
    'Float':    'sh_float_u50',        # Float < 50M (kichik float)
    'Change':   'ta_change_u',         # Bugun o'sgan
    'RSI':      'ta_rsi_nos50',        # RSI > 50
}

# --- Texnik Tahlil Sozlamalari ---
EMA_SHORT     = 9              # Qisqa EMA
EMA_LONG      = 21             # Uzun EMA
RSI_PERIOD    = 14             # RSI davri
RSI_OVERSOLD  = 40             # RSI pastki chegarasi
RSI_OVERBOUGHT= 70             # RSI yuqori chegarasi
MACD_FAST     = 12
MACD_SLOW     = 26
MACD_SIGNAL   = 9
VOLUME_MULT   = 1.5            # O'rtacha volumedan necha marta ko'p bo'lishi kerak

# --- Savdo Vaqti (New York vaqti, ET) ---
MARKET_OPEN   = '09:30'
MARKET_CLOSE  = '15:45'        # 15:45 da yangi savdo ochmaymiz
SCAN_INTERVAL = 300            # Har necha sekundda skaner ishlasin (5 daqiqa)

# --- Maksimal Cheklovlar ---
MAX_POSITIONS  = 5             # Bir vaqtda maksimal ochiq pozitsiya soni
MAX_DAILY_LOSS = 3.0           # Kunlik maksimal zarar (depozitdan %)

# --- Timeframe ---
TIMEFRAME = '5 mins'           # Tahlil uchun vaqt oralig'i
BAR_COUNT = 100                # Nechta sham olish

# --- Log Fayl ---
LOG_FILE = 'logs/trading_bot.log'
TRADE_LOG = 'logs/trades.csv'
