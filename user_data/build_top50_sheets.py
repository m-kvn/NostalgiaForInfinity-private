import sys
from pathlib import Path

import pandas as pd

from freqtrade.data.btanalysis import load_backtest_data, load_backtest_stats


BASE = Path("user_data/backtest_results")
OUT = BASE / "sheets" / "TOP50"


def sheet1(zip_path: Path) -> pd.DataFrame:
    t = load_backtest_data(zip_path).sort_values("open_date").reset_index(drop=True)
    t["trade_id"] = t.index + 1
    t["hold_hours"] = (t["close_date"] - t["open_date"]).dt.total_seconds() / 3600.0
    t["profit_pct"] = t["profit_ratio"] * 100
    df = pd.DataFrame(
        {
            "trade_id": t["trade_id"],
            "pair": t["pair"],
            "entry_date": t["open_date"].dt.strftime("%Y-%m-%d %H:%M"),
            "entry_price": t["open_rate"].round(4),
            "exit_date": t["close_date"].dt.strftime("%Y-%m-%d %H:%M"),
            "exit_price": t["close_rate"].round(4),
            "price_move_pct": ((t["close_rate"] / t["open_rate"] - 1) * 100).round(3),
            "shares": t["amount"],
            "entry_cost": (t["open_rate"] * t["amount"]).round(2),
            "exit_value": (t["close_rate"] * t["amount"]).round(2),
            "hold_hours": t["hold_hours"].round(1),
            "entry_condition": t["enter_tag"],
            "exit_condition": t["exit_reason"],
            "profit_pct": t["profit_pct"].round(3),
        }
    )
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "SHEET1_entry_exit_prices.csv", index=False)
    return t


def sheet2(t: pd.DataFrame, zip_path: Path, strategy: str, wallet: float) -> None:
    t = t.copy()
    t["trade_id"] = range(1, len(t) + 1)
    t["cum_pnl"] = t["profit_abs"].cumsum()
    t["equity"] = wallet + t["cum_pnl"]
    t["equity_pct"] = (t["equity"] / wallet - 1) * 100

    per_trade = pd.DataFrame(
        {
            "trade_id": t["trade_id"],
            "pair": t["pair"],
            "close_date": t["close_date"].dt.strftime("%Y-%m-%d %H:%M"),
            "stake": t["stake_amount"].round(2),
            "profit_usd": t["profit_abs"].round(2),
            "profit_pct": (t["profit_ratio"] * 100).round(3),
            "cumulative_pnl_usd": t["cum_pnl"].round(2),
            "account_equity_usd": t["equity"].round(2),
            "account_return_pct": t["equity_pct"].round(3),
        }
    )
    per_trade.to_csv(OUT / "SHEET2_pnl_10000usd_per_trade.csv", index=False)

    mo = (
        t.set_index("close_date")
        .groupby(pd.Grouper(freq="MS"))
        .agg(
            trades=("profit_abs", "size"),
            wins=("profit_abs", lambda s: int((s > 0).sum())),
            profit_usd=("profit_abs", "sum"),
        )
    )
    mo = mo[mo["trades"] > 0]
    mo["winrate_pct"] = (mo["wins"] / mo["trades"] * 100).round(2)
    mo["profit_usd"] = mo["profit_usd"].round(2)
    mo["cumulative_usd"] = mo["profit_usd"].cumsum().round(2)
    mo["equity_usd"] = (wallet + mo["cumulative_usd"]).round(2)
    mo["return_pct"] = ((mo["equity_usd"] / wallet - 1) * 100).round(2)
    mo.to_csv(OUT / "SHEET2_pnl_10000usd_monthly.csv")

    wins = t[t["profit_abs"] > 0]
    losses = t[t["profit_abs"] <= 0]
    st = load_backtest_stats(zip_path).get("strategy", {}).get(strategy, {})
    rows = [
        ("starting_capital_usd", round(wallet, 2)),
        ("ending_capital_usd", round(wallet + t["profit_abs"].sum(), 2)),
        ("net_profit_usd", round(t["profit_abs"].sum(), 2)),
        ("roi_pct", round(st.get("profit_total", 0) * 100, 2)),
        ("cagr_pct", round(st.get("cagr", 0) * 100, 2)),
        ("period", f"{str(t['open_date'].min())[:10]} to {str(t['close_date'].max())[:10]}"),
        ("trades", len(t)),
        ("pairs_traded", t["pair"].nunique()),
        ("wins", len(wins)),
        ("losses", len(losses)),
        ("win_rate_pct", round(len(wins) / len(t) * 100, 2)),
        ("gross_profit_usd", round(wins["profit_abs"].sum(), 2)),
        ("gross_loss_usd", round(losses["profit_abs"].sum(), 2)),
        (
            "profit_factor",
            round(abs(wins["profit_abs"].sum() / losses["profit_abs"].sum()), 2)
            if len(losses)
            else "inf",
        ),
        ("max_drawdown_pct", round(st.get("max_drawdown_account", 0) * 100, 2)),
        ("best_trade_pct", round(t["profit_ratio"].max() * 100, 2)),
        ("worst_trade_pct", round(t["profit_ratio"].min() * 100, 2)),
        ("avg_trade_pct", round(t["profit_ratio"].mean() * 100, 3)),
        ("avg_profit_per_trade_usd", round(t["profit_abs"].mean(), 2)),
        ("sharpe", round(st.get("sharpe", 0), 2)),
    ]
    pd.DataFrame(rows, columns=["metric", "value"]).to_csv(
        OUT / "SHEET2_pnl_10000usd_summary.csv", index=False
    )
    print(f"  net profit on ${wallet:,.0f}: ${t['profit_abs'].sum():,.2f}")
    print(f"  ROI {st.get('profit_total', 0) * 100:.2f}%  trades={len(t)}")


if __name__ == "__main__":
    zp = Path(sys.argv[1])
    wallet = float(sys.argv[2]) if len(sys.argv) > 2 else 10000.0
    strat = sys.argv[3] if len(sys.argv) > 3 else "NfiX7Roi30"
    t = sheet1(zp)
    sheet2(t, zp, strat, wallet)
    print(f"  sheets -> {OUT}")
