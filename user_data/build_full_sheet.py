import sys
from pathlib import Path

import pandas as pd

from freqtrade.data.btanalysis import load_backtest_data


BASE = Path("user_data/backtest_results")
OUT = BASE / "sheets"

RUNS = {
    "1YEAR_with_grinding": ("backtest-result-2026-09-01_06-39-03.zip", "NfiX7SLA30"),
    "1YEAR_final_no_grinding": ("backtest-result-2026-09-02_03-16-29.zip", "NfiX7Roi30"),
}


def build(label: str, zip_name: str) -> dict | None:
    p = BASE / zip_name
    if not p.exists():
        cands = list(BASE.glob(zip_name.replace(".zip", "*")))
        if not cands:
            print(f"  !! {zip_name} not found")
            return None
        p = cands[0]

    t = load_backtest_data(p)
    if t.empty:
        return None
    t = t.sort_values("open_date").reset_index(drop=True)
    t["trade_id"] = t.index + 1
    t["duration_h"] = (t["close_date"] - t["open_date"]).dt.total_seconds() / 3600.0
    t["profit_pct"] = t["profit_ratio"] * 100
    t["n_orders"] = t["orders"].apply(len)
    t["n_buys"] = t["orders"].apply(lambda os_: sum(1 for o in os_ if o["ft_order_side"] == "buy"))
    t["n_sells"] = t["orders"].apply(
        lambda os_: sum(1 for o in os_ if o["ft_order_side"] == "sell")
    )
    t["grinded"] = t["n_buys"] > 1

    d = OUT / label
    d.mkdir(parents=True, exist_ok=True)

    trade_cols = [
        "trade_id", "pair", "open_date", "close_date", "duration_h",
        "enter_tag", "exit_reason", "open_rate", "close_rate", "amount",
        "stake_amount", "max_stake_amount", "profit_abs", "profit_pct",
        "n_buys", "n_sells", "grinded", "min_rate", "max_rate",
        "initial_stop_loss_abs", "stop_loss_abs",
    ]
    trade_cols = [c for c in trade_cols if c in t.columns]
    t[trade_cols].rename(
        columns={
            "enter_tag": "buy_condition",
            "exit_reason": "sell_condition",
            "open_rate": "buy_price",
            "close_rate": "sell_price",
        }
    ).to_csv(d / "1_trades.csv", index=False)

    rows = []
    for _, tr in t.iterrows():
        for i, o in enumerate(tr["orders"], start=1):
            ts = o.get("order_filled_timestamp")
            rows.append(
                {
                    "trade_id": tr["trade_id"],
                    "pair": tr["pair"],
                    "order_seq": i,
                    "side": o.get("ft_order_side"),
                    "kind": (
                        "initial_buy"
                        if o.get("ft_is_entry") and i == 1
                        else "GRIND_BUY"
                        if o.get("ft_is_entry")
                        else "sell"
                    ),
                    "filled_at": pd.to_datetime(ts, unit="ms", utc=True) if ts else None,
                    "price": o.get("safe_price"),
                    "amount": o.get("amount"),
                    "cost": o.get("cost"),
                    "condition": (o.get("ft_order_tag") or "").strip(),
                    "trade_buy_condition": tr["enter_tag"],
                    "trade_sell_condition": tr["exit_reason"],
                    "trade_profit_abs": tr["profit_abs"],
                    "trade_profit_pct": round(tr["profit_pct"], 4),
                }
            )
    orders = pd.DataFrame(rows)
    orders.to_csv(d / "2_orders_incl_grinding.csv", index=False)

    orders.groupby(["kind", "side"]).agg(
        orders=("cost", "size"), total_cost=("cost", "sum"), avg_price=("price", "mean")
    ).to_csv(d / "3_order_type_summary.csv")

    t.groupby("enter_tag").agg(
        trades=("profit_abs", "size"),
        wins=("profit_abs", lambda s: int((s > 0).sum())),
        profit_abs=("profit_abs", "sum"),
        avg_pct=("profit_ratio", lambda s: s.mean() * 100),
    ).sort_values("trades", ascending=False).to_csv(d / "4_by_buy_condition.csv")

    t.groupby("exit_reason").agg(
        trades=("profit_abs", "size"),
        wins=("profit_abs", lambda s: int((s > 0).sum())),
        profit_abs=("profit_abs", "sum"),
        avg_pct=("profit_ratio", lambda s: s.mean() * 100),
    ).sort_values("trades", ascending=False).to_csv(d / "5_by_sell_condition.csv")

    pp = t.groupby("pair").agg(
        trades=("profit_abs", "size"),
        wins=("profit_abs", lambda s: int((s > 0).sum())),
        profit_abs=("profit_abs", "sum"),
        avg_pct=("profit_ratio", lambda s: s.mean() * 100),
        avg_hold_h=("duration_h", "mean"),
    ).sort_values("profit_abs", ascending=False)
    pp["winrate_pct"] = pp["wins"] / pp["trades"] * 100
    pp.to_csv(d / "6_by_pair.csv")

    mo = t.set_index("close_date").groupby(pd.Grouper(freq="MS")).agg(
        trades=("profit_abs", "size"),
        wins=("profit_abs", lambda s: int((s > 0).sum())),
        profit_abs=("profit_abs", "sum"),
    )
    mo = mo[mo["trades"] > 0]
    mo["winrate_pct"] = mo["wins"] / mo["trades"] * 100
    mo["cumulative_pnl"] = mo["profit_abs"].cumsum()
    mo.to_csv(d / "7_by_month.csv")

    print(
        f"  {label}: {len(t)} trades, {len(orders)} orders "
        f"({int((orders['kind'] == 'GRIND_BUY').sum())} grind buys), "
        f"{str(t['open_date'].min())[:10]} -> {str(t['close_date'].max())[:10]}"
    )
    return {"label": label, "trades": len(t), "orders": len(orders)}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for label, (z, _strat) in RUNS.items():
        build(label, z)
