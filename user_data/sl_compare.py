import os
import re
import sys


PATS = {
    "trades": r"Trades\s+:\s+(\d+)",
    "winrate": r"Win rate\s+:\s+([\d.]+)",
    "wl": r"Wins / Losses\s+:\s+(\d+ / \d+)",
    "roi": r"ROI \(total profit\)\s+:\s+([-\d.,]+)",
    "maxdd": r"Max drawdown\s+:\s+([-\d.,]+)",
    "pf": r"Profit factor\s+:\s+([\d.,]+)",
    "worst": r"Best / worst trade\s+:\s+[-\d.,]+% / ([-\d.,]+)",
    "slexits": r"stop_loss\s+(\d+)",
    "forced": r"force_exit\s+(\d+)",
}


def main(tmp: str, tags: list[str]) -> None:
    hdr = f"{'variant':9}{'stop':>7}{'trades':>8}{'winrate':>10}{'ROI':>8}{'maxDD':>8}{'PF':>7}{'worst':>9}{'SLexits':>9}{'forced':>8}"
    print(hdr)
    print("-" * len(hdr))
    for tag in tags:
        f = os.path.join(tmp, f"pnl_{tag}.txt")
        if not os.path.exists(f):
            continue
        t = open(f, encoding="utf-8", errors="ignore").read()
        v = {}
        for k, p in PATS.items():
            m = re.search(p, t)
            v[k] = m.group(1) if m else "-"
        stop = "-" + tag[3:].lstrip("0") + "%"
        print(
            f"{tag:9}{stop:>7}{v['trades']:>8}{v['winrate'] + '%':>10}{v['roi'] + '%':>8}"
            f"{v['maxdd'] + '%':>8}{v['pf']:>7}{v['worst'] + '%':>9}{v['slexits']:>9}{v['forced']:>8}"
        )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
