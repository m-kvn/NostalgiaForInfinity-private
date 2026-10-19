from NfiX7StocksK020 import NfiX7StocksK020


class NfiX7Hold336(NfiX7StocksK020):
    stoploss = -0.30
    position_adjustment_enable = False
    minimal_roi = {"0": 0.03}
    max_hold_hours = 336

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        held_h = (current_time - trade.open_date_utc).total_seconds() / 3600.0
        if held_h >= self.max_hold_hours:
            return "max_hold"
        return super().custom_exit(pair, trade, current_time, current_rate, current_profit, **kwargs)

    def confirm_trade_exit(
        self, pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
    ) -> bool:
        if exit_reason in ("stop_loss", "trailing_stop_loss", "roi", "max_hold"):
            return True
        return super().confirm_trade_exit(
            pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
        )
