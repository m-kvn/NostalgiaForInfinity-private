import os
import re
import sys


PATS = {
    "trades": r"Trades\s+:\s+(\d+)",
    "winrate": r"Win rate\s+:\s+([\d.]+)",
    "roi": r"ROI \(total profit\)\s+:\s+([-\d.,]+)",
    "cagr": r"CAGR\s+:\s+([-\d.,]+)",
    "maxdd": r"Max drawdown\s+:\s+([-\d.,]+)",
    "pf": r"Profit factor\s+:\s+([\d.,]+)",
    "dur": r"Avg duration\s+:\s+([\d.,]+)",
    "pnl": r"NET P&L\s+:\s+([-\d.,]+)",
}

RUNS = [
    ("k=.20 1x stake", "pnl_SLA30"),
    ("k=.20 4x stake", "pnl_HI_NfiX7SLA30"),
    ("exit .60 + 4x", "pnl_NfiX7EE60"),
    ("exit .40 + 4x", "pnl_NfiX7EE40"),
    ("exit .25 + 4x", "pnl_NfiX7EE25"),
]


def main(tmp: str) -> None:
    hdr = (
        f"{'config':18}{'trades':>8}{'winrate':>9}{'ROI':>8}{'CAGR':>8}"
        f"{'maxDD':>8}{'PF':>7}{'avg hold':>10}"
    )
    print(hdr)
    print("-" * len(hdr))
    for label, fname in RUNS:
        path = os.path.join(tmp, fname + ".txt")
        if not os.path.exists(path):
            print(f"{label:18}  (missing)")
            continue
        text = open(path, encoding="utf-8", errors="ignore").read()
        v = {}
        for key, pat in PATS.items():
            m = re.search(pat, text)
            v[key] = m.group(1) if m else "-"
        print(
            f"{label:18}{v['trades']:>8}{v['winrate'] + '%':>9}{v['roi'] + '%':>8}"
            f"{v['cagr'] + '%':>8}{v['maxdd'] + '%':>8}{v['pf']:>7}{v['dur'] + 'h':>10}"
        )


if __name__ == "__main__":
    main(sys.argv[1])
