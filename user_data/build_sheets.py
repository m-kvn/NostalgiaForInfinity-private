import csv
import os
import sys
from pathlib import Path

from freqtrade.data.btanalysis import load_backtest_data, load_backtest_stats


RUNS = {
    "backtest-result-2026-09-02_03-16-29.zip": ("FINAL_out_of_sample", "NfiX7Roi30"),
    "backtest-result-2026-09-02_02-32-33.zip": ("maxhold_168h", "NfiX7Hold168"),
    "backtest-result-2026-09-02_02-11-24.zip": ("FINAL_in_sample", "NfiX7Roi30"),
    "backtest-result-2026-09-02_01-44-27.zip": ("no_grinding", "NfiX7NoGrind"),
}

BASE = Path("user_data/backtest_results")
OUT = BASE / "sheets"


def summarize(zip_name, label, strategy):
    p = BASE / zip_name
    if not p.exists():
        return None
    trades = load_backtest_data(p)
    if trades.empty:
        return None
    d = OUT / label
    d.mkdir(parents=True, exist_ok=True)

    trades = trades.sort_values("open_date").reset_index(drop=True)
    trades["duration_h"] = (
        trades["close_date"] - trades["open_date"]
    ).dt.total_seconds() / 3600.0
    trades["profit_pct"] = trades["profit_ratio"] * 100
    cols = [
        c
        for c in [
            "pair", "open_date", "close_date", "duration_h", "amount", "stake_amount",
            "open_rate", "close_rate", "profit_abs", "profit_pct", "enter_tag", "exit_reason",
        ]
        if c in trades.columns
    ]
    trades[cols].to_csv(d / "trades.csv", index=False)

    per_pair = (
        trades.groupby("pair")
        .agg(
            trades=("profit_abs", "size"),
            wins=("profit_abs", lambda s: int((s > 0).sum())),
            profit_abs=("profit_abs", "sum"),
            avg_profit_pct=("profit_ratio", lambda s: s.mean() * 100),
            avg_dur_h=("duration_h", "mean"),
        )
        .sort_values("profit_abs", ascending=False)
    )
    per_pair["winrate_pct"] = per_pair["wins"] / per_pair["trades"] * 100
    per_pair.to_csv(d / "by_pair.csv")

    monthly = (
        trades.set_index("close_date")
        .groupby(__import__("pandas").Grouper(freq="MS"))
        .agg(
            trades=("profit_abs", "size"),
            wins=("profit_abs", lambda s: int((s > 0).sum())),
            profit_abs=("profit_abs", "sum"),
        )
    )
    monthly = monthly[monthly["trades"] > 0]
    monthly["winrate_pct"] = monthly["wins"] / monthly["trades"] * 100
    monthly["cumulative"] = monthly["profit_abs"].cumsum()
    monthly.to_csv(d / "by_month.csv")

    trades.groupby("exit_reason").agg(
        trades=("profit_abs", "size"), profit_abs=("profit_abs", "sum")
    ).sort_values("trades", ascending=False).to_csv(d / "by_exit_reason.csv")

    wins = trades[trades["profit_abs"] > 0]
    losses = trades[trades["profit_abs"] <= 0]
    st = load_backtest_stats(p).get("strategy", {}).get(strategy, {})
    return {
        "run": label,
        "strategy": strategy,
        "start": str(trades["open_date"].min())[:10],
        "end": str(trades["close_date"].max())[:10],
        "trades": len(trades),
        "pairs": trades["pair"].nunique(),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 2),
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": round(trades["profit_abs"].sum(), 2),
        "roi_pct": round(st.get("profit_total", 0) * 100, 2),
        "cagr_pct": round(st.get("cagr", 0) * 100, 2),
        "max_dd_pct": round(st.get("max_drawdown_account", 0) * 100, 2),
        "profit_factor": round(abs(wins["profit_abs"].sum() / losses["profit_abs"].sum()), 2)
        if len(losses)
        else "inf",
        "avg_trade_pct": round(trades["profit_ratio"].mean() * 100, 3),
        "avg_hold_h": round(trades["duration_h"].mean(), 1),
        "worst_pct": round(trades["profit_ratio"].min() * 100, 2),
        "sharpe": round(st.get("sharpe", 0), 2),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for z, (label, strat) in RUNS.items():
        r = summarize(z, label, strat)
        if r:
            rows.append(r)
            print(f"  wrote sheets/{label}/  ({r['trades']} trades)")
    if rows:
        with open(OUT / "SUMMARY.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\n  wrote sheets/SUMMARY.csv  ({len(rows)} runs)")


if __name__ == "__main__":
    main()
