import csv
import sys
from datetime import datetime


def load(path):
    rows = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        rows.append(
            {
                "open": datetime.fromisoformat(r["open_date"]),
                "close": datetime.fromisoformat(r["close_date"]),
                "stake": (
                    abs(float(r["profit_abs"]) / float(r["profit_ratio"]))
                    if abs(float(r["profit_ratio"])) > 1e-9
                    else float(r["stake_amount"])
                ),
                "abs": float(r["profit_abs"]),
                "ratio": float(r["profit_ratio"]),
            }
        )
    return sorted(rows, key=lambda x: x["open"])


def simulate(rows, wallet, mult):
    """Replay trades in open order, skipping any that would exceed available capital."""
    events = []
    open_pos = []
    deployed = 0.0
    peak = 0.0
    pnl = 0.0
    taken = skipped = 0
    equity_min = wallet

    for t in rows:
        # close any positions that finished before this one opens
        open_pos.sort(key=lambda x: x["close"])
        while open_pos and open_pos[0]["close"] <= t["open"]:
            p = open_pos.pop(0)
            deployed -= p["size"]
            pnl += p["pnl"]

        size = t["stake"] * mult
        if deployed + size > wallet + pnl:
            skipped += 1
            continue
        open_pos.append({"close": t["close"], "size": size, "pnl": t["abs"] * mult})
        deployed += size
        taken += 1
        peak = max(peak, deployed)
        equity_min = min(equity_min, wallet + pnl - 0.0)

    for p in open_pos:
        pnl += p["pnl"]

    years = (max(r["close"] for r in rows) - min(r["open"] for r in rows)).days / 365.25
    return {
        "mult": mult,
        "taken": taken,
        "skipped": skipped,
        "pnl": pnl,
        "roi": pnl / wallet * 100,
        "cagr": ((1 + pnl / wallet) ** (1 / years) - 1) * 100,
        "peak_pct": peak / wallet * 100,
    }


def main(path, wallet=1_000_000.0):
    rows = load(path)
    print(f"trades={len(rows)}  wallet=${wallet:,.0f}")
    hdr = f"{'stake x':>8}{'taken':>7}{'skipped':>8}{'peak use':>10}{'net P&L':>14}{'ROI':>9}{'CAGR':>9}"
    print(hdr)
    print("-" * len(hdr))
    for m in [1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6]:
        r = simulate(rows, wallet, m)
        print(
            f"{m:>8.1f}{r['taken']:>7}{r['skipped']:>8}{r['peak_pct']:>9.1f}%"
            f"{r['pnl']:>14,.0f}{r['roi']:>8.2f}%{r['cagr']:>8.2f}%"
        )


if __name__ == "__main__":
    main(*sys.argv[1:])
