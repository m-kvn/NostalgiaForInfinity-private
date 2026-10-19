import io
import re
import sys


LONG_END = 27006

PROFIT = re.compile(r"(?P<pre>current_profit\s*(?P<op>>=|>|<=|<)\s*)(?P<val>0\.\d+)")


def calibrate_exits(src: str, out: str, cls_old: str, cls_new: str, e: float) -> int:
    text = io.open(src, encoding="utf-8").read()
    lines = text.split("\n")
    head, tail = lines[:LONG_END], lines[LONG_END:]
    body = "\n".join(tail)

    def scale(m: re.Match) -> str:
        v = float(m.group("val"))
        return m.group("pre") + f"{v * e:.6f}"

    body, n = PROFIT.subn(scale, body)
    new_text = "\n".join(head + body.split("\n"))
    new_text = new_text.replace(f"class {cls_old}(IStrategy):", f"class {cls_new}(IStrategy):", 1)
    io.open(out, "w", encoding="utf-8", newline="\n").write(new_text)
    compile(new_text, out, "exec")
    return n


SUB = '''from {base_mod} import {base_cls}


class {cls}({base_cls}):
    stoploss = -0.30

    def confirm_trade_exit(
        self, pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
    ) -> bool:
        if exit_reason in ("stop_loss", "trailing_stop_loss"):
            return True
        return super().confirm_trade_exit(
            pair, trade, order_type, amount, rate, time_in_force, exit_reason, current_time, **kwargs
        )
'''


if __name__ == "__main__":
    e = float(sys.argv[1])
    tag = sys.argv[2]
    src_cls = "NfiX7CalK020"
    src = f"user_data/strategies/{src_cls}Base.py"
    new_cls = f"NfiX7Exit{tag}"
    base_mod = f"{new_cls}Base"
    n = calibrate_exits(src, f"user_data/strategies/{base_mod}.py", src_cls, new_cls, e)

    # the exit-calibrated base still needs the stocks adaptations from the K020 subclass
    stocks = io.open("user_data/strategies/NfiX7StocksK020.py", encoding="utf-8").read()
    stocks = stocks.replace("NfiX7CalK020Base", base_mod).replace("NfiX7CalK020", new_cls)
    stocks = stocks.replace("class NfiX7StocksK020(", f"class {new_cls}Stocks(")
    io.open(f"user_data/strategies/{new_cls}Stocks.py", "w", encoding="utf-8", newline="\n").write(
        stocks
    )

    cls = f"NfiX7E{tag}"
    io.open(f"user_data/strategies/{cls}.py", "w", encoding="utf-8", newline="\n").write(
        SUB.format(base_mod=f"{new_cls}Stocks", base_cls=f"{new_cls}Stocks", cls=cls)
    )
    print(f"e={e} -> {cls}  ({n} exit thresholds scaled)")
