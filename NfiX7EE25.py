from NfiX7ExitE25Stocks import NfiX7ExitE25Stocks


class NfiX7EE25(NfiX7ExitE25Stocks):
    stoploss = -0.30

    def confirm_trade_exit(
        self, pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
    ) -> bool:
        if exit_reason in ("stop_loss", "trailing_stop_loss"):
            return True
        return super().confirm_trade_exit(
            pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
        )
