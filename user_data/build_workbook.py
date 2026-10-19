import sys
from pathlib import Path

import pandas as pd

from freqtrade.data.btanalysis import load_backtest_data, load_backtest_stats


BASE = Path("user_data/backtest_results")
OUT = BASE / "NfiX7_top50_results.xlsx"

WALLET = 10000.0
ZIP_10K = "backtest-result-2026-09-02_04-20-49.zip"
ZIP_1M = "backtest-result-2026-09-02_03-48-07.zip"


def prep(zp: Path) -> pd.DataFrame:
    t = load_backtest_data(zp).sort_values("open_date").reset_index(drop=True)
    t["trade_id"] = t.index + 1
    t["hold_hours"] = (t["close_date"] - t["open_date"]).dt.total_seconds() / 3600.0
    t["profit_pct"] = t["profit_ratio"] * 100
    return t


def s_prices(t: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_id": t["trade_id"],
            "pair": t["pair"],
            "entry_date": t["open_date"].dt.tz_localize(None),
            "entry_price": t["open_rate"].round(4),
            "exit_date": t["close_date"].dt.tz_localize(None),
            "exit_price": t["close_rate"].round(4),
            "price_move_%": ((t["close_rate"] / t["open_rate"] - 1) * 100).round(3),
            "shares": t["amount"],
            "entry_cost": (t["open_rate"] * t["amount"]).round(2),
            "exit_value": (t["close_rate"] * t["amount"]).round(2),
            "hold_hours": t["hold_hours"].round(1),
            "entry_condition": t["enter_tag"],
            "exit_condition": t["exit_reason"],
            "profit_%": t["profit_pct"].round(3),
        }
    )


def s_pnl(t: pd.DataFrame, wallet: float) -> pd.DataFrame:
    c = t["profit_abs"].cumsum()
    return pd.DataFrame(
        {
            "trade_id": t["trade_id"],
            "pair": t["pair"],
            "close_date": t["close_date"].dt.tz_localize(None),
            "stake_usd": t["stake_amount"].round(2),
            "profit_usd": t["profit_abs"].round(2),
            "profit_%": (t["profit_ratio"] * 100).round(3),
            "cumulative_pnl_usd": c.round(2),
            "account_equity_usd": (wallet + c).round(2),
            "account_return_%": ((wallet + c) / wallet * 100 - 100).round(3),
        }
    )


def s_monthly(t: pd.DataFrame, wallet: float) -> pd.DataFrame:
    m = (
        t.set_index("close_date")
        .groupby(pd.Grouper(freq="MS"))
        .agg(
            trades=("profit_abs", "size"),
            wins=("profit_abs", lambda s: int((s > 0).sum())),
            profit_usd=("profit_abs", "sum"),
        )
    )
    m = m[m["trades"] > 0].reset_index()
    m["month"] = m["close_date"].dt.tz_localize(None).dt.strftime("%Y-%m")
    m["winrate_%"] = (m["wins"] / m["trades"] * 100).round(2)
    m["profit_usd"] = m["profit_usd"].round(2)
    m["cumulative_usd"] = m["profit_usd"].cumsum().round(2)
    m["equity_usd"] = (wallet + m["cumulative_usd"]).round(2)
    m["return_%"] = ((m["equity_usd"] / wallet - 1) * 100).round(2)
    return m[
        ["month", "trades", "wins", "winrate_%", "profit_usd", "cumulative_usd",
         "equity_usd", "return_%"]
    ]


def s_group(t: pd.DataFrame, key: str, name: str) -> pd.DataFrame:
    g = (
        t.groupby(key)
        .agg(
            trades=("profit_abs", "size"),
            wins=("profit_abs", lambda s: int((s > 0).sum())),
            profit_usd=("profit_abs", "sum"),
            avg_profit_pct=("profit_ratio", lambda s: s.mean() * 100),
            avg_hold_h=("hold_hours", "mean"),
        )
        .sort_values("profit_usd", ascending=False)
        .reset_index()
    )
    g["winrate_%"] = (g["wins"] / g["trades"] * 100).round(2)
    g["profit_usd"] = g["profit_usd"].round(2)
    g["avg_profit_pct"] = g["avg_profit_pct"].round(3)
    g["avg_hold_h"] = g["avg_hold_h"].round(1)
    return g.rename(columns={key: name})


def s_summary(t: pd.DataFrame, zp: Path, wallet: float) -> pd.DataFrame:
    w, l = t[t["profit_abs"] > 0], t[t["profit_abs"] <= 0]
    st = load_backtest_stats(zp).get("strategy", {}).get("NfiX7Roi30", {})
    rows = [
        ("Strategy", "NfiX7Roi30 (X7 calibrated k=0.20)"),
        ("Universe", "Top 50 US stocks (49 traded, BRK.B unavailable)"),
        ("Period", f"{str(t['open_date'].min())[:10]} to {str(t['close_date'].max())[:10]}"),
        ("Stoploss", "-30% (enforced)"),
        ("Grinding", "disabled"),
        ("", ""),
        ("Starting capital (USD)", round(wallet, 2)),
        ("Ending capital (USD)", round(wallet + t["profit_abs"].sum(), 2)),
        ("Net profit (USD)", round(t["profit_abs"].sum(), 2)),
        ("ROI %", round(st.get("profit_total", 0) * 100, 2)),
        ("CAGR %", round(st.get("cagr", 0) * 100, 2)),
        ("", ""),
        ("Trades", len(t)),
        ("Pairs traded", t["pair"].nunique()),
        ("Wins", len(w)),
        ("Losses", len(l)),
        ("Win rate %", round(len(w) / len(t) * 100, 2)),
        ("Gross profit (USD)", round(w["profit_abs"].sum(), 2)),
        ("Gross loss (USD)", round(l["profit_abs"].sum(), 2)),
        ("Profit factor", round(abs(w["profit_abs"].sum() / l["profit_abs"].sum()), 2) if len(l) else "inf"),
        ("Max drawdown %", round(st.get("max_drawdown_account", 0) * 100, 2)),
        ("Best trade %", round(t["profit_ratio"].max() * 100, 2)),
        ("Worst trade %", round(t["profit_ratio"].min() * 100, 2)),
        ("Avg trade %", round(t["profit_ratio"].mean() * 100, 3)),
        ("Avg profit/trade (USD)", round(t["profit_abs"].mean(), 2)),
        ("Avg hold (hours)", round(t["hold_hours"].mean(), 1)),
        ("Sharpe", round(st.get("sharpe", 0), 2)),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def main() -> None:
    z10 = BASE / ZIP_10K
    t10 = prep(z10)
    sheets = {
        "Summary_10k": s_summary(t10, z10, WALLET),
        "1_Entry_Exit_Prices": s_prices(t10),
        "2_PnL_10000_per_trade": s_pnl(t10, WALLET),
        "3_PnL_10000_monthly": s_monthly(t10, WALLET),
        "4_By_Pair": s_group(t10, "pair", "pair"),
        "5_By_Entry_Condition": s_group(t10, "enter_tag", "entry_condition"),
        "6_By_Exit_Condition": s_group(t10, "exit_reason", "exit_condition"),
    }

    z1m = BASE / ZIP_1M
    if z1m.exists():
        t1m = prep(z1m)
        sheets["7_Ref_1M_wallet_trades"] = s_prices(t1m)
        sheets["8_Ref_1M_monthly"] = s_monthly(t1m, 1_000_000.0)

    with pd.ExcelWriter(OUT, engine="xlsxwriter", datetime_format="yyyy-mm-dd hh:mm") as xl:
        book = xl.book
        hdr = book.add_format(
            {"bold": True, "bg_color": "#1F3864", "font_color": "white", "border": 1}
        )
        money = book.add_format({"num_format": "#,##0.00"})
        pct = book.add_format({"num_format": "0.000"})
        for name, df in sheets.items():
            df.to_excel(xl, sheet_name=name[:31], index=False)
            ws = xl.sheets[name[:31]]
            for i, col in enumerate(df.columns):
                width = max(len(str(col)) + 2, min(int(df[col].astype(str).str.len().max() or 8) + 2, 34))
                fmt = money if "usd" in col.lower() or "price" in col.lower() or "cost" in col.lower() or "value" in col.lower() else (pct if "%" in col else None)
                ws.set_column(i, i, width, fmt)
                ws.write(0, i, col, hdr)
            ws.freeze_panes(1, 0)
            if len(df) > 1:
                ws.autofilter(0, 0, len(df), len(df.columns) - 1)
        print(f"  wrote {OUT}")
        for n, d in sheets.items():
            print(f"    {n:26} {len(d):>6} rows")


if __name__ == "__main__":
    main()
