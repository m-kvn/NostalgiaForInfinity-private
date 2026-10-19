from NfiX7StocksK020 import NfiX7StocksK020


class NfiX7RoiT(NfiX7StocksK020):
    stoploss = -0.30
    position_adjustment_enable = False
    minimal_roi = {"0": 0.04, "120": 0.02, "480": 0.01, "1440": 0.005}

    def confirm_trade_exit(
        self, pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
    ) -> bool:
        if exit_reason in ("stop_loss", "trailing_stop_loss", "roi"):
            return True
        return super().confirm_trade_exit(
            pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
        )
