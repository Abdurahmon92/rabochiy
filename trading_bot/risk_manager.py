# ============================================================
#  Risk Menejment Moduli
#  1-2% risk, 1:2 RR, Trailing Stop, 50% qisman yopish
# ============================================================

from logger import logger, log_trade
from config import (
    RISK_PERCENT, REWARD_RATIO,
    PARTIAL_CLOSE_PERCENT, TRAILING_STOP_PERCENT,
    MAX_POSITIONS, MAX_DAILY_LOSS
)
from ib_insync import MarketOrder, LimitOrder, StopOrder


class RiskManager:

    def __init__(self, ibkr_conn):
        self.ib           = ibkr_conn.ib
        self.ibkr         = ibkr_conn
        self.daily_loss   = 0.0       # Kunlik zarar kuzatuvi
        self.daily_pnl    = 0.0       # Kunlik P&L
        # { symbol: { qty, entry, stop, target, partial_done, trail_stop } }
        self.open_trades  = {}

    # ----------------------------------------------------------
    # Pozitsiya hajmini hisoblash
    # ----------------------------------------------------------

    def calculate_position_size(self, entry_price, stop_price, account_size=None):
        """
        Risk asosida pozitsiya hajmini hisoblash.

        Misol:
            Depozit:    $10,000
            Risk:       1.5% = $150
            Entry:      $100
            Stop-Loss:  $97  → risk per share = $3
            Qty = $150 / $3 = 50 ta aksiya
        """
        if account_size is None:
            account_size = self.ibkr.get_account_value()

        if not account_size or account_size <= 0:
            logger.error("Hisob qiymatini olishda xato")
            return 0

        risk_amount    = account_size * (RISK_PERCENT / 100)
        risk_per_share = abs(entry_price - stop_price)

        if risk_per_share <= 0:
            logger.error("Stop-loss narxi kirish narxiga teng yoki yuqori!")
            return 0

        qty = int(risk_amount / risk_per_share)

        # Minimal tekshiruv
        if qty < 1:
            logger.warning(
                f"Pozitsiya hajmi juda kichik: {qty} | "
                f"Risk: ${risk_amount:.2f} | Risk/share: ${risk_per_share:.2f}"
            )
            return 0

        logger.info(
            f"📐 Pozitsiya hajmi: {qty} ta aksiya | "
            f"Hisob: ${account_size:,.2f} | "
            f"Risk: ${risk_amount:.2f} ({RISK_PERCENT}%) | "
            f"Risk/share: ${risk_per_share:.2f}"
        )
        return qty

    # ----------------------------------------------------------
    # Kunlik cheklov tekshiruvi
    # ----------------------------------------------------------

    def can_trade(self):
        """Savdo qilish mumkinmi?"""
        # Ochiq pozitsiyalar soni
        positions = self.ibkr.get_positions()
        if len(positions) >= MAX_POSITIONS:
            logger.warning(
                f"⛔ Maksimal pozitsiya soni: {len(positions)}/{MAX_POSITIONS}"
            )
            return False

        # Kunlik zarar chegarasi
        account_size = self.ibkr.get_account_value()
        if account_size:
            max_loss = account_size * (MAX_DAILY_LOSS / 100)
            if self.daily_loss >= max_loss:
                logger.warning(
                    f"⛔ Kunlik zarar chegarasi: ${self.daily_loss:.2f} / ${max_loss:.2f}"
                )
                return False

        return True

    # ----------------------------------------------------------
    # Pozitsiya ochish
    # ----------------------------------------------------------

    def open_position(self, symbol, entry_price, stop_price, target_price, signal_reason=''):
        """
        Yangi pozitsiya ochish:
        1. Pozitsiya hajmini hisoblash
        2. Market order berish
        3. Stop-loss order berish
        4. Savdoni ro'yxatga olish
        """
        if not self.can_trade():
            return False

        # Allaqachon ochiq pozitsiya bor?
        if symbol in self.open_trades:
            logger.warning(f"⚠️  {symbol} da pozitsiya allaqachon mavjud")
            return False

        qty = self.calculate_position_size(entry_price, stop_price)
        if qty <= 0:
            return False

        try:
            contract = self.ibkr.get_contract(symbol)
            if not contract:
                return False

            # --- Market order (sotib olish) ---
            buy_order = MarketOrder('BUY', qty)
            buy_trade = self.ib.placeOrder(contract, buy_order)
            self.ib.sleep(1)

            actual_entry = float(
                buy_trade.orderStatus.avgFillPrice or entry_price
            )

            # --- Stop-Loss order ---
            sl_order = StopOrder('SELL', qty, stop_price)
            sl_order.transmit = True
            self.ib.placeOrder(contract, sl_order)

            # --- Savdoni saqlash ---
            half_qty    = qty // 2
            target_half = round(
                actual_entry + (actual_entry - stop_price) * 1.0, 4
            )  # 1:1 darajasi (50% yopish uchun)

            self.open_trades[symbol] = {
                'qty':          qty,
                'remaining':    qty,
                'entry':        actual_entry,
                'stop':         stop_price,
                'target':       target_price,
                'target_half':  target_half,   # 1:1 darajasi
                'partial_done': False,         # 50% yopildimi?
                'trail_stop':   stop_price,    # Trailing stop joriy darajasi
                'half_qty':     half_qty,
                'contract':     contract,
            }

            log_trade(
                'BUY', symbol, qty, actual_entry,
                stop_price, target_price, signal_reason
            )
            logger.info(
                f"✅ {symbol} pozitsiya ochildi! "
                f"Qty: {qty} | Entry: ${actual_entry:.2f} | "
                f"SL: ${stop_price:.2f} | TP: ${target_price:.2f} | "
                f"1:1 daraja: ${target_half:.2f}"
            )
            return True

        except Exception as e:
            logger.error(f"{symbol} pozitsiyasini ochishda xato: {e}")
            return False

    # ----------------------------------------------------------
    # Trailing Stop va Qisman Yopish
    # ----------------------------------------------------------

    def manage_position(self, symbol, current_price):
        """
        Ochiq pozitsiyani boshqarish:
        1. Narx 1:1 ga yetsa → 50% yopish
        2. Qolgan 50% uchun → trailing stop yangilash
        3. Stop-loss urilsa → butunlay yopish
        """
        if symbol not in self.open_trades:
            return

        trade = self.open_trades[symbol]
        entry      = trade['entry']
        stop       = trade['stop']
        target_h   = trade['target_half']
        target     = trade['target']
        remaining  = trade['remaining']
        trail_stop = trade['trail_stop']

        # --- Stop-loss urildi? ---
        if current_price <= stop:
            logger.warning(
                f"🛑 {symbol} Stop-Loss urildi! "
                f"Narx: ${current_price:.2f} | SL: ${stop:.2f}"
            )
            self._close_position(symbol, remaining, 'STOP_LOSS')
            return

        # --- Take-Profit (to'liq) ---
        if current_price >= target:
            logger.info(
                f"🎯 {symbol} Take-Profit! "
                f"Narx: ${current_price:.2f} | TP: ${target:.2f}"
            )
            self._close_position(symbol, remaining, 'TAKE_PROFIT')
            return

        # --- 1:1 ga yetdi → 50% yopish ---
        if not trade['partial_done'] and current_price >= target_h:
            half_qty = trade['half_qty']
            logger.info(
                f"✂️  {symbol} 1:1 darajaga yetdi! "
                f"{PARTIAL_CLOSE_PERCENT}% yopilmoqda "
                f"({half_qty} ta aksiya) | Narx: ${current_price:.2f}"
            )
            self._partial_close(symbol, half_qty, current_price)
            trade['partial_done'] = True
            trade['remaining']    = remaining - half_qty

            # Trailing stop → entry ga ko'chirish (breakeven)
            trade['trail_stop'] = entry
            trade['stop']       = entry
            self._update_stop_order(symbol, entry, trade['remaining'])
            logger.info(
                f"🔒 {symbol} Stop → Breakeven: ${entry:.2f}"
            )
            return

        # --- Trailing Stop yangilash (faqat 50% yopilgandan keyin) ---
        if trade['partial_done']:
            new_trail = round(
                current_price * (1 - TRAILING_STOP_PERCENT / 100), 4
            )
            if new_trail > trail_stop:
                logger.info(
                    f"📈 {symbol} Trailing Stop yangilandi: "
                    f"${trail_stop:.2f} → ${new_trail:.2f}"
                )
                trade['trail_stop'] = new_trail
                trade['stop']       = new_trail
                self._update_stop_order(symbol, new_trail, trade['remaining'])

    # ----------------------------------------------------------
    # Yordamchi metodlar
    # ----------------------------------------------------------

    def _partial_close(self, symbol, qty, current_price):
        """Pozitsiyaning bir qismini yopish"""
        try:
            trade    = self.open_trades[symbol]
            contract = trade['contract']

            close_order = MarketOrder('SELL', qty)
            self.ib.placeOrder(contract, close_order)
            self.ib.sleep(0.5)

            pnl = (current_price - trade['entry']) * qty
            self.daily_pnl += pnl

            log_trade(
                'PARTIAL_SELL', symbol, qty, current_price,
                trade['stop'], trade['target'],
                f'50% yopildi | PnL: ${pnl:.2f}'
            )
            logger.info(
                f"✂️  {symbol} 50% yopildi | "
                f"Qty: {qty} | PnL: ${pnl:.2f}"
            )
        except Exception as e:
            logger.error(f"{symbol} qisman yopishda xato: {e}")

    def _close_position(self, symbol, qty, reason=''):
        """Pozitsiyani to'liq yopish"""
        try:
            trade    = self.open_trades[symbol]
            contract = trade['contract']

            close_order = MarketOrder('SELL', qty)
            self.ib.placeOrder(contract, close_order)
            self.ib.sleep(1)

            current_price = self.ibkr.get_current_price(symbol) or trade['entry']
            pnl = (current_price - trade['entry']) * qty
            self.daily_pnl  += pnl
            if pnl < 0:
                self.daily_loss += abs(pnl)

            log_trade(
                'SELL', symbol, qty, current_price,
                trade['stop'], trade['target'],
                f'{reason} | PnL: ${pnl:.2f}'
            )
            logger.info(
                f"🔴 {symbol} pozitsiya yopildi | "
                f"Sabab: {reason} | PnL: ${pnl:.2f}"
            )

            # Ro'yxatdan o'chirish
            del self.open_trades[symbol]

        except Exception as e:
            logger.error(f"{symbol} pozitsiyasini yopishda xato: {e}")

    def _update_stop_order(self, symbol, new_stop, qty):
        """Stop-loss orderni yangilash"""
        try:
            contract = self.open_trades[symbol]['contract']

            # Eski stop orderlarni bekor qilish
            for order in self.ib.openOrders():
                if (hasattr(order, 'action') and
                        order.action == 'SELL' and
                        order.orderType == 'STP'):
                    self.ib.cancelOrder(order)
                    self.ib.sleep(0.3)
                    break

            # Yangi stop order berish
            new_stop_order = StopOrder('SELL', qty, new_stop)
            self.ib.placeOrder(contract, new_stop_order)

        except Exception as e:
            logger.error(f"{symbol} stop orderni yangilashda xato: {e}")

    def close_all_positions(self, reason='EOD'):
        """Barcha pozitsiyalarni yopish (kun oxiri)"""
        symbols = list(self.open_trades.keys())
        for symbol in symbols:
            trade = self.open_trades.get(symbol)
            if trade:
                logger.info(f"🔴 {symbol} yopilmoqda — {reason}")
                self._close_position(symbol, trade['remaining'], reason)

    def get_daily_summary(self):
        """Kunlik hisobot"""
        logger.info(
            f"\n{'='*50}\n"
            f"📊 KUNLIK HISOBOT\n"
            f"  Jami P&L:  ${self.daily_pnl:+.2f}\n"
            f"  Zarar:     ${self.daily_loss:.2f}\n"
            f"  Pozitsiyalar: {len(self.open_trades)}\n"
            f"{'='*50}"
        )
        return {
            'pnl':       self.daily_pnl,
            'loss':      self.daily_loss,
            'positions': len(self.open_trades),
        }
