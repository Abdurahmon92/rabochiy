# ============================================================
#  Finviz Skaner Moduli
#  Kuchli aksiyalarni avtomatik topadi
# ============================================================

import requests
import pandas as pd
from bs4 import BeautifulSoup
from logger import logger
from config import FINVIZ_FILTERS


class FinvizScanner:
    BASE_URL = "https://finviz.com/screener.ashx"
    HEADERS = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    def __init__(self):
        self.filters = self._build_filters()

    def _build_filters(self):
        """Finviz filtrlarini URL formatiga o'tkazish"""
        filter_map = {
            # Birja
            'Exchange':  {
                'NASDAQ':       'exch_nasd',
                'NYSE':         'exch_nyse',
                'NASDAQ,NYSE':  'exch_nasd,exch_nyse',
            },
            # Narx
            'Price': {
                'sh_price_o5':   'sh_price_o5',
                'sh_price_o10':  'sh_price_o10',
                'sh_price_o20':  'sh_price_o20',
            },
            # Volume
            'Volume': {
                'sh_avgvol_o500':  'sh_avgvol_o500',
                'sh_avgvol_o1000': 'sh_avgvol_o1000',
            },
            # Float
            'Float': {
                'sh_float_u50':  'sh_float_u50',
                'sh_float_u100': 'sh_float_u100',
            },
            # O'zgarish
            'Change': {
                'ta_change_u':  'ta_change_u',
                'ta_change_d':  'ta_change_d',
            },
            # RSI
            'RSI': {
                'ta_rsi_nos50':  'ta_rsi_nos50',
                'ta_rsi_nos60':  'ta_rsi_nos60',
            },
        }

        filters = []
        for key, value in FINVIZ_FILTERS.items():
            if key in filter_map and value in filter_map[key]:
                filters.append(filter_map[key][value])
            else:
                filters.append(value)

        return filters

    def scan(self):
        """
        Finviz dan aksiyalar ro'yxatini olish.
        Qaytaradi: ['AAPL', 'TSLA', ...] — symbol ro'yxati
        """
        try:
            params = {
                'v': '111',
                'f': ','.join(self.filters),
                'o': '-volume',        # Volumega ko'ra saralash
            }

            logger.info("🔍 Finviz skaneri ishlamoqda...")
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.HEADERS,
                timeout=15
            )
            response.raise_for_status()

            symbols = self._parse_symbols(response.text)
            logger.info(f"✅ Finviz: {len(symbols)} ta aksiya topildi → {symbols[:10]}")
            return symbols

        except requests.exceptions.Timeout:
            logger.error("❌ Finviz so'rovi vaqt tugadi (timeout)")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Finviz so'rovida xato: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Finviz skaner xatosi: {e}")
            return []

    def _parse_symbols(self, html):
        """HTML dan ticker symbollarini ajratib olish"""
        symbols = []
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Finviz jadvalini topish
            table = soup.find('table', {'id': 'screener-views-table'})
            if not table:
                # Yangi Finviz layout
                table = soup.find('table', class_='screener_table')

            if not table:
                # Ticker linklaridan olish
                links = soup.find_all('a', class_='screener-link-primary')
                for link in links:
                    text = link.text.strip()
                    if text and len(text) <= 5 and text.isupper():
                        symbols.append(text)
                return symbols[:50]

            rows = table.find_all('tr')[1:]  # Sarlavhani o'tkazib yuborish
            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 1:
                    ticker = cols[1].text.strip()
                    if ticker and len(ticker) <= 5 and ticker.isupper():
                        symbols.append(ticker)

        except Exception as e:
            logger.error(f"HTML parse xatosi: {e}")

        return symbols[:50]  # Maksimal 50 ta aksiya

    def get_stock_info(self, symbol):
        """
        Bitta aksiya haqida batafsil ma'lumot olish.
        Qaytaradi: dict yoki None
        """
        try:
            url = f"https://finviz.com/quote.ashx?t={symbol}"
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            info = {}

            # Asosiy ma'lumotlar jadvalidan olish
            table = soup.find('table', class_='snapshot-table2')
            if table:
                cells = table.find_all('td')
                for i in range(0, len(cells) - 1, 2):
                    key   = cells[i].text.strip()
                    value = cells[i + 1].text.strip()
                    info[key] = value

            # Muhim qiymatlarni olish
            result = {
                'symbol':    symbol,
                'price':     float(info.get('Price', 0) or 0),
                'change':    info.get('Change', '0%'),
                'volume':    info.get('Volume', '0'),
                'avg_vol':   info.get('Avg Volume', '0'),
                'float':     info.get('Float', 'N/A'),
                'rsi':       float(info.get('RSI (14)', 0) or 0),
                'atr':       float(info.get('ATR', 0) or 0),
                'sector':    info.get('Sector', 'N/A'),
                'industry':  info.get('Industry', 'N/A'),
                'earnings':  info.get('Earnings', 'N/A'),
            }
            return result

        except Exception as e:
            logger.warning(f"{symbol} ma'lumotini olishda xato: {e}")
            return None

    def filter_by_criteria(self, symbols, ibkr_conn):
        """
        Topilgan aksiyalarni qo'shimcha tekshiruvdan o'tkazish.
        Faqat eng kuchli signallilarini qaytaradi.
        """
        qualified = []

        for symbol in symbols[:20]:  # Birinchi 20 tasini tekshir
            try:
                info = self.get_stock_info(symbol)
                if not info:
                    continue

                # Earning oldidan savdo qilmaymiz
                earnings = info.get('earnings', '')
                if earnings and earnings not in ['-', 'N/A']:
                    if 'Today' in earnings or 'Tomorrow' in earnings:
                        logger.debug(
                            f"⏭️  {symbol} o'tkazildi — earning yaqin: {earnings}"
                        )
                        continue

                # RSI tekshirish
                rsi = info.get('rsi', 0)
                if rsi > 0 and (rsi < 40 or rsi > 75):
                    logger.debug(
                        f"⏭️  {symbol} o'tkazildi — RSI: {rsi}"
                    )
                    continue

                qualified.append(symbol)
                logger.debug(f"✅ {symbol} — RSI: {rsi}, qualified")

            except Exception as e:
                logger.warning(f"{symbol} filtrda xato: {e}")
                continue

        logger.info(
            f"🎯 Filtrdan o'tgan aksiyalar: {len(qualified)} ta → {qualified}"
        )
        return qualified
