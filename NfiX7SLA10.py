from NfiX7StocksK020 import NfiX7StocksK020


class NfiX7SLA10(NfiX7StocksK020):
    stoploss = -0.1
    position_adjustment_enable = True
    max_entry_position_adjustment = -1

    def confirm_trade_exit(
        self, pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
    ) -> bool:
        if exit_reason in ("stop_loss", "trailing_stop_loss"):
            return True
        return super().confirm_trade_exit(
            pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
        )
