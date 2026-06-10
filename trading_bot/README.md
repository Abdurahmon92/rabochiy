# 🤖 IBKR Algoritmik Trading Bot

## 📋 Bot Qanday Ishlaydi

```
Finviz Skaner → Texnik Tahlil → Signal → Risk Hisob → Order → IBKR → Birja
```

### Savdo Logikasi:
- **Kirish:** EMA kesishish + RSI + MACD + Volume surge signali
- **Risk:** Depozitning 1.5% (sozlanadi)
- **Reward:** 1:2 nisbat
- **50% yopish:** Narx 1:1 darajaga yetganda
- **Trailing Stop:** 50% yopilgandan keyin avtomatik
- **Kun oxiri:** 15:45 ET da barcha pozitsiyalar yopiladi

---

## 🛠️ O'rnatish (Windows)

### 1. Python o'rnatish
- https://python.org dan Python 3.10+ yuklab oling
- O'rnatishda **"Add to PATH"** ni belgilang ✅

### 2. IBKR TWS yoki IB Gateway o'rnatish
- https://www.interactivebrokers.com/en/trading/tws.php
- **TWS (Trader Workstation)** yuklab oling
- Hisobingiz bilan kiring

### 3. TWS sozlamalari
```
TWS → Edit → Global Configuration → API → Settings:
  ✅ Enable ActiveX and Socket Clients
  ✅ Allow connections from localhost only
  Socket port: 7497  (Paper) yoki 7496 (Live)
  ✅ Read-Only API: O'CHIRING (bot order bera olishi uchun)
```

### 4. Bot fayllarini o'rnatish
```bash
# Papka yarating
mkdir C:\trading_bot
cd C:\trading_bot

# Fayllarni ko'chiring (barcha .py fayllarni)

# Kutubxonalarni o'rnatish
pip install -r requirements.txt
```

### 5. config.py ni sozlash
```python
# config.py faylini oching va o'zgartiring:

ACCOUNT_SIZE = 10000      # Sizning depozitingiz
RISK_PERCENT = 1.5        # Risk foizi (1-2)
IBKR_PORT    = 7497       # Paper: 7497 | Live: 7496
```

---

## 🖥️ O'rnatish (Mac/Linux)

```bash
# Python tekshirish
python3 --version

# Virtual muhit yaratish
python3 -m venv venv
source venv/bin/activate

# Kutubxonalar
pip install -r requirements.txt

# Botni ishga tushirish
python3 bot.py
```

---

## 🚀 Ishga Tushirish

```bash
# 1. Avval TWS yoki IB Gateway ni oching va kiring

# 2. Botni ishga tushiring
python bot.py

# Natija:
# ============================================================
# 🤖 IBKR Algoritmik Trading Bot ishga tushmoqda...
# ============================================================
# ✅ IBKR ga ulandi! Host: 127.0.0.1, Port: 7497
# 💰 Hisob qiymati: $10,000.00
# ✅ Bot muvaffaqiyatli ishga tushdi!
```

---

## 📁 Fayl Strukturasi

```
trading_bot/
│
├── bot.py                 ← Asosiy fayl (shu ni ishga tushiring)
├── config.py              ← Sozlamalar (shu ni o'zgartiring)
├── ibkr_connection.py     ← IBKR ulanish
├── finviz_scanner.py      ← Aksiya qidiruvchi
├── technical_analysis.py  ← RSI, EMA, MACD tahlili
├── risk_manager.py        ← Risk, trailing stop, 50% yopish
├── logger.py              ← Loglash
├── requirements.txt       ← Kutubxonalar
│
├── logs/
│   ├── trading_bot.log    ← Bot loglari
│   └── trades.csv         ← Savdo tarixi
```

---

## ⚙️ Muhim Sozlamalar (config.py)

| Sozlama | Default | Ma'nosi |
|---------|---------|---------|
| `ACCOUNT_SIZE` | 10000 | Depozit ($) |
| `RISK_PERCENT` | 1.5 | Bir savdodagi risk (%) |
| `REWARD_RATIO` | 2.0 | Risk/Reward (1:2) |
| `PARTIAL_CLOSE_PERCENT` | 50 | 1:1 da yopiladigan % |
| `TRAILING_STOP_PERCENT` | 1.0 | Trailing stop masofasi (%) |
| `MAX_POSITIONS` | 5 | Maksimal ochiq pozitsiya |
| `MAX_DAILY_LOSS` | 3.0 | Kunlik max zarar (%) |
| `SCAN_INTERVAL` | 300 | Skaner intervali (sekund) |
| `IBKR_PORT` | 7497 | TWS port (7497=paper, 7496=live) |

---

## ⚠️ Muhim Ogohlantirishlar

### 🔴 PAPER TRADING bilan boshlang!
```python
# config.py da:
IBKR_PORT = 7497   # Paper trading (xavfsiz)
# IBKR_PORT = 7496  # Live trading (real pul) — tayyor bo'lganda
```

### 📋 Pattern Day Trader qoidasi
- $25,000 dan kam kapital bo'lsa → kuniga max **3 ta** savdo
- $25,000 dan ko'p bo'lsa → cheksiz savdo

### 🕐 Bozor vaqti
- NYSE/NASDAQ: **09:30 — 16:00 ET** (New York vaqti)
- O'zbekiston vaqti: **17:30 — 00:00** (yozda) / **18:30 — 01:00** (qishda)

---

## 🔧 Muammolar va Yechimlar

| Muammo | Yechim |
|--------|--------|
| `Connection refused` | TWS/Gateway ochiq emasligini tekshiring |
| `Port already in use` | TWS ni qayta ishga tushiring |
| `No data for symbol` | Market data subscription tekshiring |
| `Order rejected` | Hisob turini tekshiring (paper/live) |

---

## 📞 Bot To'xtatish
```
Ctrl + C  — botni xavfsiz to'xtatish
```

---

*⚠️ Disclaimer: Bu bot ta'lim maqsadida yaratilgan. Real pul bilan savdo qilishdan oldin paper trading bilan sinab ko'ring. Moliyaviy maslahat uchun mutaxassisga murojaat qiling.*
