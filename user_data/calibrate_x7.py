import io
import re
import sys


SRC = "user_data/strategies/NostalgiaForInfinityX7.py"
LONG_START, LONG_END = 13827, 27006

MULT = re.compile(
    r"(?P<lhs>[A-Za-z_][\w]*)\s*(?P<op><=|>=|<|>)\s*\(?\s*"
    r"(?P<rhs>[A-Za-z_][\w]*)\s*\*\s*(?P<val>[01]\.\d+)\s*\)?"
)
FRAC = re.compile(
    r"(?P<pre>\(\s*[A-Za-z_][\w]*\s*[-+]\s*[A-Za-z_][\w]*\s*\)\s*(?P<op>>=|>|<=|<)\s*\(\s*"
    r"(?P<base>open_rate|open|close|close_15m)\s*\*\s*)(?P<val>0\.0\d+)"
)
BBB = re.compile(r"(?P<pre>bbb_[\w]*\s*>\s*)(?P<val>\d+\.\d+)")
EMASPREAD = re.compile(r"(?P<pre>/\s*close\s*\*\s*100\.0\s*\)\s*(?P<op>>|<)\s*)(?P<val>-?\d+\.\d+)")


def scale_mult(m: re.Match, k: float) -> str:
    v = float(m.group("val"))
    op = m.group("op")
    restrictive = (op in ("<", "<=") and v < 1.0) or (op in (">", ">=") and v > 1.0)
    if not restrictive:
        return m.group(0)
    new = 1.0 - (1.0 - v) * k if v < 1.0 else 1.0 + (v - 1.0) * k
    return m.group(0).replace(m.group("val"), f"{new:.6f}")


def calibrate(k: float, out_path: str, class_name: str) -> dict:
    text = io.open(SRC, encoding="utf-8").read()
    lines = text.split("\n")
    head, seg, tail = (
        lines[: LONG_START - 1],
        lines[LONG_START - 1 : LONG_END],
        lines[LONG_END:],
    )
    body = "\n".join(seg)
    counts = {}

    body, counts["mult"] = MULT.subn(lambda m: scale_mult(m, k), body)
    body, counts["frac"] = FRAC.subn(
        lambda m: m.group("pre") + f"{float(m.group('val')) * k:.6f}", body
    )
    body, counts["bbb"] = BBB.subn(
        lambda m: m.group("pre") + f"{float(m.group('val')) * k:.4f}", body
    )
    body, counts["emaspread"] = EMASPREAD.subn(
        lambda m: m.group("pre") + f"{float(m.group('val')) * k:.4f}", body
    )

    new_text = "\n".join(head + body.split("\n") + tail)
    new_text = new_text.replace(
        "class NostalgiaForInfinityX7(IStrategy):", f"class {class_name}(IStrategy):", 1
    )
    io.open(out_path, "w", encoding="utf-8", newline="\n").write(new_text)
    compile(new_text, out_path, "exec")
    return counts


SUBCLASS = '''import logging

import {base_mod} as _nfi_module
from pandas import DataFrame

from {base_mod} import {base_cls}


logger = logging.getLogger(__name__)

_orig_merge = _nfi_module.merge_informative_pair


def _merge_ffill(dataframe, informative, timeframe, timeframe_inf, **kwargs):
    kwargs["ffill"] = True
    return _orig_merge(dataframe, informative, timeframe, timeframe_inf, **kwargs)


_nfi_module.merge_informative_pair = _merge_ffill


class {cls}({base_cls}):
    INTERFACE_VERSION = 3
    startup_candle_count: int = 2100
    bad_trade_controller_enable = False
    short_entry_signal_params = dict.fromkeys({base_cls}.short_entry_signal_params, False)

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
'''


if __name__ == "__main__":
    k = float(sys.argv[1])
    tag = sys.argv[2]
    base_cls = f"NfiX7Cal{tag}"
    base_mod = f"{base_cls}Base"
    c = calibrate(k, f"user_data/strategies/{base_mod}.py", base_cls)
    cls = f"NfiX7Stocks{tag}"
    sub = SUBCLASS.format(base_mod=base_mod, base_cls=base_cls, cls=cls)
    io.open(f"user_data/strategies/{cls}.py", "w", encoding="utf-8", newline="\n").write(sub)
    print(f"k={k} -> {cls} (base {base_mod}) rewrites={sum(c.values())} {c}")
