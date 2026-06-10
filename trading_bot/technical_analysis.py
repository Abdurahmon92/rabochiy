# ============================================================
#  Texnik Tahlil Moduli
#  RSI, EMA, MACD, Volume tahlili
# ============================================================

import pandas as pd
import numpy as np
from logger import logger
from config import (
    EMA_SHORT, EMA_LONG,
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    VOLUME_MULT
)


class TechnicalAnalysis:

    # ----------------------------------------------------------
    # Indikatorlarni hisoblash
    # ----------------------------------------------------------

    @staticmethod
    def calculate_ema(series, period):
        """EMA (Exponential Moving Average) hisoblash"""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(series, period=14):
        """RSI (Relative Strength Index) hisoblash"""
        delta = series.diff()
        gain  = delta.clip(lower=0)
        loss  = -delta.clip(upper=0)

        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

        rs  = avg_gain / avg_loss.replace(0, np.finfo(float).eps)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_macd(series, fast=12, slow=26, signal=9):
        """MACD hisoblash — (macd_line, signal_line, histogram)"""
        ema_fast   = series.ewm(span=fast,   adjust=False).mean()
        ema_slow   = series.ewm(span=slow,   adjust=False).mean()
        macd_line  = ema_fast - ema_slow
        signal_line= macd_line.ewm(span=signal, adjust=False).mean()
        histogram  = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_atr(df, period=14):
        """ATR (Average True Range) hisoblash"""
        high  = df['high']
        low   = df['low']
        close = df['close']

        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs()
        ], axis=1).max(axis=1)

        return tr.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_vwap(df):
        """VWAP (Volume Weighted Average Price) hisoblash"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap

    # ----------------------------------------------------------
    # Signal generatsiyasi
    # ----------------------------------------------------------

    def analyze(self, df, symbol=''):
        """
        To'liq tahlil qilish va signal qaytarish.

        Qaytaradi:
            {
              'signal':   'BUY' | 'SELL' | 'HOLD',
              'strength': 0-100  (signal kuchi),
              'entry':    float  (kirish narxi),
              'stop':     float  (stop-loss narxi),
              'target':   float  (take-profit narxi),
              'reason':   str    (sabab),
              'indicators': dict
            }
        """
        if df is None or len(df) < 50:
            logger.warning(f"{symbol}: Yetarli ma'lumot yo'q ({len(df) if df is not None else 0} sham)")
            return self._no_signal('Yetarli ma\'lumot yo\'q')

        try:
            close  = df['close']
            volume = df['volume']

            # --- Indikatorlarni hisoblash ---
            ema_short  = self.calculate_ema(close, EMA_SHORT)
            ema_long   = self.calculate_ema(close, EMA_LONG)
            rsi        = self.calculate_rsi(close, RSI_PERIOD)
            macd, macd_sig, macd_hist = self.calculate_macd(
                close, MACD_FAST, MACD_SLOW, MACD_SIGNAL
            )
            atr        = self.calculate_atr(df)
            vwap       = self.calculate_vwap(df)

            # So'nggi qiymatlar
            curr_price      = float(close.iloc[-1])
            curr_ema_short  = float(ema_short.iloc[-1])
            curr_ema_long   = float(ema_long.iloc[-1])
            prev_ema_short  = float(ema_short.iloc[-2])
            prev_ema_long   = float(ema_long.iloc[-2])
            curr_rsi        = float(rsi.iloc[-1])
            curr_macd       = float(macd.iloc[-1])
            curr_macd_sig   = float(macd_sig.iloc[-1])
            prev_macd       = float(macd.iloc[-2])
            prev_macd_sig   = float(macd_sig.iloc[-2])
            curr_atr        = float(atr.iloc[-1])
            curr_vwap       = float(vwap.iloc[-1])
            avg_volume      = float(volume.rolling(20).mean().iloc[-1])
            curr_volume     = float(volume.iloc[-1])

            indicators = {
                'price':      curr_price,
                'ema_short':  round(curr_ema_short, 4),
                'ema_long':   round(curr_ema_long,  4),
                'rsi':        round(curr_rsi, 2),
                'macd':       round(curr_macd, 4),
                'macd_sig':   round(curr_macd_sig, 4),
                'atr':        round(curr_atr, 4),
                'vwap':       round(curr_vwap, 4),
                'volume':     int(curr_volume),
                'avg_volume': int(avg_volume),
            }

            # --- BUY shartlari ---
            ema_crossover_up = (
                prev_ema_short <= prev_ema_long and
                curr_ema_short >  curr_ema_long
            )
            ema_trend_up     = curr_ema_short > curr_ema_long
            rsi_ok_buy       = RSI_OVERSOLD < curr_rsi < RSI_OVERBOUGHT
            macd_cross_up    = (
                prev_macd <= prev_macd_sig and
                curr_macd >  curr_macd_sig
            )
            macd_positive    = curr_macd > 0
            price_above_vwap = curr_price > curr_vwap
            volume_surge     = curr_volume > avg_volume * VOLUME_MULT

            # --- SELL shartlari ---
            ema_crossover_dn = (
                prev_ema_short >= prev_ema_long and
                curr_ema_short <  curr_ema_long
            )
            rsi_overbought   = curr_rsi > RSI_OVERBOUGHT
            macd_cross_dn    = (
                prev_macd >= prev_macd_sig and
                curr_macd <  curr_macd_sig
            )

            # --- Signal kuchini hisoblash (0-100) ---
            buy_score  = 0
            sell_score = 0
            reasons    = []

            # BUY ballari
            if ema_crossover_up:
                buy_score += 30
                reasons.append("EMA kesishdi (yuqoriga)")
            elif ema_trend_up:
                buy_score += 15
                reasons.append("EMA trend yuqori")

            if rsi_ok_buy:
                buy_score += 20
                reasons.append(f"RSI normal: {curr_rsi:.1f}")

            if macd_cross_up:
                buy_score += 25
                reasons.append("MACD kesishdi (yuqoriga)")
            elif macd_positive:
                buy_score += 10
                reasons.append("MACD musbat")

            if price_above_vwap:
                buy_score += 15
                reasons.append("Narx VWAP dan yuqori")

            if volume_surge:
                buy_score += 10
                reasons.append(f"Volume kuchli: {curr_volume/avg_volume:.1f}x")

            # SELL ballari
            if ema_crossover_dn:
                sell_score += 35
            if rsi_overbought:
                sell_score += 25
            if macd_cross_dn:
                sell_score += 25
            if not price_above_vwap:
                sell_score += 15

            # --- Stop va Target hisoblash (ATR asosida) ---
            stop_distance   = curr_atr * 1.5
            target_distance = stop_distance * 2.0   # 1:2 RR

            buy_stop   = round(curr_price - stop_distance, 4)
            buy_target = round(curr_price + target_distance, 4)

            # --- Qaror ---
            if buy_score >= 60 and buy_score > sell_score:
                logger.info(
                    f"📈 {symbol} BUY signal | Kuch: {buy_score} | "
                    f"Narx: {curr_price} | SL: {buy_stop} | TP: {buy_target} | "
                    f"Sabab: {', '.join(reasons)}"
                )
                return {
                    'signal':     'BUY',
                    'strength':   buy_score,
                    'entry':      curr_price,
                    'stop':       buy_stop,
                    'target':     buy_target,
                    'atr':        curr_atr,
                    'reason':     ', '.join(reasons),
                    'indicators': indicators,
                }

            elif sell_score >= 60:
                logger.info(f"📉 {symbol} SELL signal | Kuch: {sell_score}")
                return {
                    'signal':     'SELL',
                    'strength':   sell_score,
                    'entry':      curr_price,
                    'stop':       None,
                    'target':     None,
                    'atr':        curr_atr,
                    'reason':     'Chiqish signali',
                    'indicators': indicators,
                }

            else:
                logger.debug(
                    f"⏸️  {symbol} HOLD | BUY: {buy_score} | SELL: {sell_score}"
                )
                return self._no_signal(
                    f"Signal kuchsiz (BUY:{buy_score}, SELL:{sell_score})",
                    indicators
                )

        except Exception as e:
            logger.error(f"{symbol} tahlilida xato: {e}")
            return self._no_signal(f"Tahlil xatosi: {e}")

    @staticmethod
    def _no_signal(reason='', indicators=None):
        return {
            'signal':     'HOLD',
            'strength':   0,
            'entry':      None,
            'stop':       None,
            'target':     None,
            'atr':        None,
            'reason':     reason,
            'indicators': indicators or {},
        }
