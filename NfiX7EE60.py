from NfiX7ExitE60Stocks import NfiX7ExitE60Stocks


class NfiX7EE60(NfiX7ExitE60Stocks):
    stoploss = -0.30

    def confirm_trade_exit(
        self, pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
    ) -> bool:
        if exit_reason in ("stop_loss", "trailing_stop_loss"):
            return True
        return super().confirm_trade_exit(
            pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
        )
