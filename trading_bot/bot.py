# ============================================================
#  IBKR Algoritmik Trading Bot — Asosiy Fayl
#  Barcha modullarni birlashtiradi va boshqaradi
# ============================================================

import time
import schedule
from datetime import datetime
import pytz

from ibkr_connection   import IBKRConnection
from finviz_scanner    import FinvizScanner
from technical_analysis import TechnicalAnalysis
from risk_manager      import RiskManager
from logger            import logger
from config            import (
    SCAN_INTERVAL, TIMEFRAME, BAR_COUNT,
    MARKET_OPEN, MARKET_CLOSE
)


class TradingBot:

    def __init__(self):
        logger.info("=" * 60)
        logger.info("🤖 IBKR Algoritmik Trading Bot ishga tushmoqda...")
        logger.info("=" * 60)

        self.ibkr      = IBKRConnection()
        self.scanner   = FinvizScanner()
        self.analyst   = TechnicalAnalysis()
        self.risk_mgr  = None          # IBKR ulangandan keyin yaratiladi
        self.running   = False
        self.watchlist = []            # Kuzatiladigan aksiyalar

    # ----------------------------------------------------------
    # Ishga tushirish va to'xtatish
    # ----------------------------------------------------------

    def start(self):
        """Botni ishga tushirish"""
        # IBKR ga ulanish
        if not self.ibkr.connect():
            logger.error("❌ IBKR ga ulanib bo'lmadi. Bot to'xtatildi.")
            return

        self.risk_mgr = RiskManager(self.ibkr)
        self.running  = True

        logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")
        logger.info(f"⏰ Bozor vaqti: {MARKET_OPEN} - {MARKET_CLOSE} ET")
        logger.info(f"🔄 Skaner intervali: {SCAN_INTERVAL} sekund")

        # Jadval sozlash
        schedule.every(SCAN_INTERVAL).seconds.do(self._trading_cycle)
        schedule.every().day.at("15:45").do(self._end_of_day)

        # Asosiy tsikl
        try:
            while self.running:
                schedule.run_pending()
                self.ibkr.keep_alive()
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("⛔ Bot foydalanuvchi tomonidan to'xtatildi.")
        except Exception as e:
            logger.error(f"❌ Bot xatosi: {e}")
        finally:
            self.stop()

    def stop(self):
        """Botni to'xtatish"""
        self.running = False
        if self.risk_mgr:
            self.risk_mgr.get_daily_summary()
        self.ibkr.disconnect()
        logger.info("🔴 Bot to'xtatildi.")

    # ----------------------------------------------------------
    # Asosiy savdo tsikli
    # ----------------------------------------------------------

    def _trading_cycle(self):
        """
        Har SCAN_INTERVAL sekundda ishlaydigan asosiy tsikl:
        1. Bozor ochiqmi?
        2. Ochiq pozitsiyalarni boshqar
        3. Yangi signal qidir
        4. Signal bo'lsa — pozitsiya och
        """
        try:
            # --- Bozor ochiqmi? ---
            if not self.ibkr.is_market_open():
                logger.debug("💤 Bozor yopiq. Kutilmoqda...")
                return

            logger.info(f"\n{'─'*50}")
            logger.info(f"🔄 Yangi tsikl: {datetime.now().strftime('%H:%M:%S')}")

            # --- Ochiq pozitsiyalarni boshqarish ---
            self._manage_open_positions()

            # --- Savdo qilish mumkinmi? ---
            if not self.risk_mgr.can_trade():
                logger.info("⛔ Yangi savdo ochish mumkin emas (limit yetdi)")
                return

            # --- Finviz skaneri ---
            logger.info("🔍 Finviz skaneri ishlamoqda...")
            raw_symbols = self.scanner.scan()

            if not raw_symbols:
                logger.warning("⚠️  Finviz dan aksiya kelmadi")
                return

            # --- Filtr ---
            symbols = self.scanner.filter_by_criteria(raw_symbols, self.ibkr)

            if not symbols:
                logger.info("📭 Filtrdan o'tgan aksiya yo'q")
                return

            # --- Har bir aksiyani tahlil qilish ---
            best_signal  = None
            best_symbol  = None
            best_strength = 0

            for symbol in symbols[:10]:  # Top 10 ni tahlil qil
                # Allaqachon ochiq pozitsiya?
                if symbol in self.risk_mgr.open_trades:
                    continue

                signal = self._analyze_symbol(symbol)

                if (signal and
                        signal['signal'] == 'BUY' and
                        signal['strength'] > best_strength):
                    best_strength = signal['strength']
                    best_signal   = signal
                    best_symbol   = symbol

            # --- Eng kuchli signalga kirish ---
            if best_signal and best_symbol:
                logger.info(
                    f"🎯 Eng kuchli signal: {best_symbol} "
                    f"(Kuch: {best_strength})"
                )
                self._execute_trade(best_symbol, best_signal)
            else:
                logger.info("📭 Hozircha signal yo'q")

        except Exception as e:
            logger.error(f"Tsikl xatosi: {e}")

    # ----------------------------------------------------------
    # Tahlil
    # ----------------------------------------------------------

    def _analyze_symbol(self, symbol):
        """Bitta aksiyani tahlil qilish"""
        try:
            # Tarixiy ma'lumot olish
            df = self.ibkr.get_historical_data(
                symbol,
                duration='2 D',
                bar_size=TIMEFRAME
            )

            if df is None or len(df) < 30:
                return None

            # Texnik tahlil
            signal = self.analyst.analyze(df, symbol)
            return signal

        except Exception as e:
            logger.error(f"{symbol} tahlilida xato: {e}")
            return None

    # ----------------------------------------------------------
    # Savdo bajarish
    # ----------------------------------------------------------

    def _execute_trade(self, symbol, signal):
        """Signal asosida savdo ochish"""
        try:
            entry  = signal['entry']
            stop   = signal['stop']
            target = signal['target']
            reason = signal['reason']

            if not entry or not stop or not target:
                logger.warning(f"{symbol}: Narx ma'lumotlari to'liq emas")
                return

            # Joriy narxni tekshirish
            current = self.ibkr.get_current_price(symbol)
            if not current:
                return

            # Narx juda uzoqlashib ketganmi?
            slippage = abs(current - entry) / entry * 100
            if slippage > 0.5:
                logger.warning(
                    f"⚠️  {symbol} narx siljidi: "
                    f"Signal: ${entry:.2f} | Joriy: ${current:.2f} "
                    f"({slippage:.2f}%)"
                )
                return

            # Pozitsiya ochish
            success = self.risk_mgr.open_position(
                symbol, current, stop, target, reason
            )

            if success:
                logger.info(
                    f"🚀 {symbol} savdo ochildi! "
                    f"Narx: ${current:.2f} | "
                    f"SL: ${stop:.2f} | TP: ${target:.2f}"
                )

        except Exception as e:
            logger.error(f"{symbol} savdo ochishda xato: {e}")

    # ----------------------------------------------------------
    # Ochiq pozitsiyalarni boshqarish
    # ----------------------------------------------------------

    def _manage_open_positions(self):
        """Barcha ochiq pozitsiyalarni boshqarish"""
        if not self.risk_mgr.open_trades:
            return

        logger.info(
            f"📋 Ochiq pozitsiyalar: "
            f"{list(self.risk_mgr.open_trades.keys())}"
        )

        for symbol in list(self.risk_mgr.open_trades.keys()):
            current_price = self.ibkr.get_current_price(symbol)
            if current_price:
                trade = self.risk_mgr.open_trades.get(symbol)
                if trade:
                    entry = trade['entry']
                    pnl   = (current_price - entry) * trade['remaining']
                    logger.info(
                        f"  📊 {symbol}: "
                        f"Kirish: ${entry:.2f} | "
                        f"Joriy: ${current_price:.2f} | "
                        f"PnL: ${pnl:+.2f} | "
                        f"SL: ${trade['stop']:.2f} | "
                        f"Partial: {'✅' if trade['partial_done'] else '⏳'}"
                    )
                self.risk_mgr.manage_position(symbol, current_price)

    # ----------------------------------------------------------
    # Kun oxiri
    # ----------------------------------------------------------

    def _end_of_day(self):
        """15:45 ET — barcha pozitsiyalarni yopish"""
        logger.info("🔔 Kun oxiri (15:45 ET) — barcha pozitsiyalar yopilmoqda...")
        self.risk_mgr.close_all_positions(reason='EOD_CLOSE')
        self.risk_mgr.get_daily_summary()
        self.watchlist = []


# ============================================================
#  Ishga tushirish
# ============================================================

if __name__ == '__main__':
    bot = TradingBot()
    bot.start()
