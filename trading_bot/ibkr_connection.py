# ============================================================
#  IBKR Ulanish Moduli
# ============================================================

from ib_insync import IB, Stock, util
from logger import logger
from config import IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID


class IBKRConnection:
    def __init__(self):
        self.ib = IB()
        self.connected = False

    def connect(self):
        """IBKR ga ulanish"""
        try:
            self.ib.connect(IBKR_HOST, IBKR_PORT, clientId=IBKR_CLIENT_ID)
            self.connected = True
            logger.info(f"✅ IBKR ga ulandi! Host: {IBKR_HOST}, Port: {IBKR_PORT}")
            self._print_account_info()
            return True
        except Exception as e:
            logger.error(f"❌ IBKR ga ulanishda xato: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """IBKR dan uzilish"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("🔌 IBKR dan uzildi.")

    def _print_account_info(self):
        """Hisob ma'lumotlarini ko'rsatish"""
        try:
            account_values = self.ib.accountValues()
            for av in account_values:
                if av.tag == 'NetLiquidation' and av.currency == 'USD':
                    logger.info(f"💰 Hisob qiymati: ${float(av.value):,.2f}")
                if av.tag == 'AvailableFunds' and av.currency == 'USD':
                    logger.info(f"💵 Mavjud mablag': ${float(av.value):,.2f}")
        except Exception as e:
            logger.warning(f"Hisob ma'lumotlarini olishda xato: {e}")

    def get_account_value(self):
        """Joriy hisob qiymatini olish"""
        try:
            account_values = self.ib.accountValues()
            for av in account_values:
                if av.tag == 'NetLiquidation' and av.currency == 'USD':
                    return float(av.value)
        except Exception as e:
            logger.error(f"Hisob qiymatini olishda xato: {e}")
        return None

    def get_available_funds(self):
        """Mavjud mablag'ni olish"""
        try:
            account_values = self.ib.accountValues()
            for av in account_values:
                if av.tag == 'AvailableFunds' and av.currency == 'USD':
                    return float(av.value)
        except Exception as e:
            logger.error(f"Mavjud mablag'ni olishda xato: {e}")
        return None

    def get_positions(self):
        """Ochiq pozitsiyalarni olish"""
        try:
            positions = self.ib.positions()
            pos_dict = {}
            for pos in positions:
                if pos.position != 0:
                    pos_dict[pos.contract.symbol] = {
                        'qty':       pos.position,
                        'avg_cost':  pos.avgCost,
                        'contract':  pos.contract
                    }
            return pos_dict
        except Exception as e:
            logger.error(f"Pozitsiyalarni olishda xato: {e}")
            return {}

    def get_open_orders(self):
        """Ochiq orderlarni olish"""
        try:
            return self.ib.openOrders()
        except Exception as e:
            logger.error(f"Ochiq orderlarni olishda xato: {e}")
            return []

    def get_contract(self, symbol):
        """Aksiya kontraktini olish"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)
            return contract
        except Exception as e:
            logger.error(f"{symbol} kontraktini olishda xato: {e}")
            return None

    def get_historical_data(self, symbol, duration='1 D', bar_size='5 mins'):
        """Tarixiy narx ma'lumotlarini olish"""
        try:
            contract = self.get_contract(symbol)
            if not contract:
                return None

            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )

            if bars:
                import pandas as pd
                df = util.df(bars)
                df.set_index('date', inplace=True)
                logger.debug(f"📊 {symbol}: {len(df)} ta sham olindi")
                return df
            else:
                logger.warning(f"{symbol} uchun ma'lumot kelmadi")
                return None

        except Exception as e:
            logger.error(f"{symbol} tarixiy ma'lumotini olishda xato: {e}")
            return None

    def get_current_price(self, symbol):
        """Joriy narxni olish"""
        try:
            contract = self.get_contract(symbol)
            if not contract:
                return None

            ticker = self.ib.reqMktData(contract, '', False, False)
            self.ib.sleep(1)

            price = ticker.last or ticker.close or ticker.bid
            self.ib.cancelMktData(contract)

            if price and price > 0:
                return float(price)
            else:
                logger.warning(f"{symbol} narxini olishda muammo")
                return None

        except Exception as e:
            logger.error(f"{symbol} narxini olishda xato: {e}")
            return None

    def is_market_open(self):
        """Bozor ochiqmi yoki yo'q"""
        from datetime import datetime
        import pytz
        et = pytz.timezone('America/New_York')
        now = datetime.now(et)

        # Dushanba(0) dan Juma(4) gacha
        if now.weekday() > 4:
            return False

        market_open  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=15, minute=45, second=0, microsecond=0)

        return market_open <= now <= market_close

    def keep_alive(self):
        """Ulanishni saqlash"""
        if self.connected:
            self.ib.sleep(0)
