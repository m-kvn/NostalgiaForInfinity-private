import sys
from pathlib import Path

import pandas as pd

from freqtrade.data.btanalysis import load_backtest_data, load_backtest_stats


pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_rows", 5000)


def main(path: str, out_dir: str = "user_data/backtest_results") -> None:
    p = Path(path)
    trades = load_backtest_data(p)
    if trades.empty:
        print("NO TRADES in", p)
        return

    trades = trades.sort_values("open_date").reset_index(drop=True)
    trades["open_date"] = pd.to_datetime(trades["open_date"], utc=True)
    trades["close_date"] = pd.to_datetime(trades["close_date"], utc=True)
    trades["duration_h"] = (
        trades["close_date"] - trades["open_date"]
    ).dt.total_seconds() / 3600.0

    cols = [
        "pair", "open_date", "close_date", "duration_h", "amount", "stake_amount",
        "open_rate", "close_rate", "profit_abs", "profit_ratio", "enter_tag", "exit_reason",
    ]
    cols = [c for c in cols if c in trades.columns]
    detail = trades[cols].copy()
    detail["profit_pct"] = detail["profit_ratio"] * 100

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    detail.to_csv(out / "trades_full.csv", index=False)

    print("=" * 110)
    print("ALL TRADES (open -> close)")
    print("=" * 110)
    print(detail.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    wins = trades[trades["profit_abs"] > 0]
    losses = trades[trades["profit_abs"] <= 0]
    gross_win = wins["profit_abs"].sum()
    gross_loss = losses["profit_abs"].sum()

    print("\n" + "=" * 110)
    print("PER-PAIR P&L")
    print("=" * 110)
    per_pair = (
        trades.groupby("pair")
        .agg(
            trades=("profit_abs", "size"),
            wins=("profit_abs", lambda s: int((s > 0).sum())),
            profit_abs=("profit_abs", "sum"),
            avg_profit_pct=("profit_ratio", lambda s: s.mean() * 100),
            best_pct=("profit_ratio", lambda s: s.max() * 100),
            worst_pct=("profit_ratio", lambda s: s.min() * 100),
            avg_dur_h=("duration_h", "mean"),
        )
        .sort_values("profit_abs", ascending=False)
    )
    per_pair["winrate_pct"] = per_pair["wins"] / per_pair["trades"] * 100
    per_pair.to_csv(out / "pnl_by_pair.csv")
    print(per_pair.to_string(float_format=lambda x: f"{x:,.2f}"))

    print("\n" + "=" * 110)
    print("MONTHLY P&L")
    print("=" * 110)
    monthly = (
        trades.set_index("close_date")
        .groupby(pd.Grouper(freq="MS"))
        .agg(
            trades=("profit_abs", "size"),
            wins=("profit_abs", lambda s: int((s > 0).sum())),
            profit_abs=("profit_abs", "sum"),
            avg_profit_pct=("profit_ratio", lambda s: s.mean() * 100),
        )
    )
    monthly = monthly[monthly["trades"] > 0]
    monthly["winrate_pct"] = monthly["wins"] / monthly["trades"] * 100
    monthly["cum_profit_abs"] = monthly["profit_abs"].cumsum()
    monthly.to_csv(out / "pnl_by_month.csv")
    print(monthly.to_string(float_format=lambda x: f"{x:,.2f}"))

    print("\n" + "=" * 110)
    print("EXIT REASONS")
    print("=" * 110)
    if "exit_reason" in trades.columns:
        er = (
            trades.groupby("exit_reason")
            .agg(
                trades=("profit_abs", "size"),
                profit_abs=("profit_abs", "sum"),
                avg_profit_pct=("profit_ratio", lambda s: s.mean() * 100),
            )
            .sort_values("trades", ascending=False)
        )
        print(er.to_string(float_format=lambda x: f"{x:,.2f}"))

    print("\n" + "=" * 110)
    print("SUMMARY")
    print("=" * 110)
    print(f"  Trades                : {len(trades)}")
    print(f"  Pairs traded          : {trades['pair'].nunique()}")
    print(f"  Period                : {trades['open_date'].min()}  ->  {trades['close_date'].max()}")
    print(f"  Wins / Losses         : {len(wins)} / {len(losses)}")
    print(f"  Win rate              : {len(wins) / len(trades) * 100:,.2f}%")
    print(f"  Gross profit          : {gross_win:,.2f}")
    print(f"  Gross loss            : {gross_loss:,.2f}")
    print(f"  NET P&L               : {trades['profit_abs'].sum():,.2f}")
    print(f"  Profit factor         : {abs(gross_win / gross_loss):,.2f}" if gross_loss else "  Profit factor         : inf")
    print(f"  Avg trade profit      : {trades['profit_ratio'].mean() * 100:,.3f}%")
    print(f"  Best / worst trade    : {trades['profit_ratio'].max() * 100:,.2f}% / {trades['profit_ratio'].min() * 100:,.2f}%")
    print(f"  Avg duration          : {trades['duration_h'].mean():,.1f} h")

    try:
        stats = load_backtest_stats(p)
        for sname, s in stats.get("strategy", {}).items():
            sc = s.get("starting_balance")
            print(f"\n  Strategy              : {sname}")
            print(f"  Starting balance      : {sc:,.2f}")
            print(f"  Final balance         : {s.get('final_balance', 0):,.2f}")
            print(f"  ROI (total profit)    : {s.get('profit_total', 0) * 100:,.2f}%")
            print(f"  Max drawdown          : {s.get('max_drawdown_account', 0) * 100:,.2f}%")
            print(f"  CAGR                  : {s.get('cagr', 0) * 100:,.2f}%")
            print(f"  Sharpe / Sortino      : {s.get('sharpe', 0):,.3f} / {s.get('sortino', 0):,.3f}")
    except Exception as e:
        print(f"  (stats unavailable: {e})")

    print(f"\n  CSVs written to {out}/ : trades_full.csv, pnl_by_pair.csv, pnl_by_month.csv")


if __name__ == "__main__":
    main(*sys.argv[1:])
