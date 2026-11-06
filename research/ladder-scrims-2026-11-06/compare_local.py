"""Live scrim results of one version against local results of the same bot on the same ladder maps and sides.

    py research/ladder-scrims-2026-11-06/compare_local.py 78 replays/batch-*-ab-lscrim-her-vs-astr1106-ladder-ladder

Local batches are ab.py runs on the 128 ladder maps with our bot first (CAND). Per map, the local score is our wins
over its two sides; the live score our wins over each opponent's two sides. Prints per-opponent win rates on the
maps both cover, and the correlation of live and local per-map scores."""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import ladder_scrims as L  # noqa: E402


def local(batch):
    d = json.loads((Path(batch) / "results.json").read_text())
    out = {}
    for m in d["matches"]:
        name = Path(m["map"]).stem.replace("-", "_")
        side = "a" if m["order"][0] == 0 else "b"
        out[(name, side)] = m["winner"] == 0
    return out


def corr(xs, ys):
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else float("nan")


def main():
    version, batches = int(sys.argv[1]), sys.argv[2:]
    live = L.games(version)
    opps = sorted({r["opp_name"] for r in live})
    for b in batches:
        loc = local(b)
        print(f"\nlocal {Path(b).name}: {100 * sum(loc.values()) / len(loc):.1f}% of {len(loc)}")
        for o in opps:
            rows = [r for r in live if r["opp_name"] == o and (r["map"], r["side"]) in loc]
            if not rows:
                continue
            w = sum(r["result"] == "win" for r in rows)
            lw = sum(loc[(r["map"], r["side"])] for r in rows)
            p, lo, hi = L.wilson(w, len(rows))
            both = sum(r["result"] == "win" and loc[(r["map"], r["side"])] for r in rows)
            maps = sorted({r["map"] for r in rows})
            xs = [sum(loc.get((m, s), 0) for s in "ab") for m in maps]
            ys = [sum(r["result"] == "win" for r in rows if r["map"] == m) for m in maps]
            print(f"  {o[:24]:<24} live {w}/{len(rows)} = {100 * p:.1f}% ({100 * lo:.1f}-{100 * hi:.1f}); "
                  f"local on the same games {100 * lw / len(rows):.1f}%; won both {both}; "
                  f"per-map correlation {corr(xs, ys):+.2f} over {len(maps)} maps")


if __name__ == "__main__":
    main()
