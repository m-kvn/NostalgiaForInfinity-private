import logging

import NfiX7CalK030Base as _nfi_module
from pandas import DataFrame

from NfiX7CalK030Base import NfiX7CalK030


logger = logging.getLogger(__name__)

_orig_merge = _nfi_module.merge_informative_pair


def _merge_ffill(dataframe, informative, timeframe, timeframe_inf, **kwargs):
    kwargs["ffill"] = True
    return _orig_merge(dataframe, informative, timeframe, timeframe_inf, **kwargs)


_nfi_module.merge_informative_pair = _merge_ffill


class NfiX7StocksK030(NfiX7CalK030):
    INTERFACE_VERSION = 3
    startup_candle_count: int = 2100
    bad_trade_controller_enable = False
    short_entry_signal_params = dict.fromkeys(NfiX7CalK030.short_entry_signal_params, False)

    def btc_informative_pair(self) -> str:
        return "SPY/USD"

    def base_tf_5m_indicators(self, metadata: dict, df: DataFrame) -> DataFrame:
        df = super().base_tf_5m_indicators(metadata, df)
        if "num_empty_288" in df.columns:
            df["num_empty_288"] = 0.0
        return df

    def correct_min_stake(self, min_stake=None, trade_leverage=None):
        min_stake = super().correct_min_stake(min_stake, trade_leverage)
        return 1.0 if min_stake is None else min_stake

    def check_entry_timeout(self, pair, trade, order, current_time, **kwargs) -> bool:
        return False

    def check_exit_timeout(self, pair, trade, order, current_time, **kwargs) -> bool:
        return False
