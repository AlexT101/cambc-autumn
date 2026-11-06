"""Turns of a 100M census whose spend before the turn-end queue is >= FLOOR: per-label inclusive/self.

    python3 research/ideas-2026-11-05/fuel5-tools/heavy.py GAMES_DIR [--floor 100000] [--with LABEL] [--prefix P]
"""
import argparse, collections, sys
sys.path.insert(0, "tools/fuel/census")
import census
ap = argparse.ArgumentParser(); ap.add_argument("dirs", nargs="+"); ap.add_argument("--floor", type=int, default=100000)
ap.add_argument("--with", dest="w"); ap.add_argument("--prefix", default=""); ap.add_argument("--top", type=int, default=60)
a = ap.parse_args()
rows = census.load(a.dirs)
pre = lambda r: census.inc(r, "turn") - census.inc(r, "queue")
big = [r for r in rows if r["round"] > 1 and pre(r) >= a.floor and (not a.w or census.inc(r, a.w) >= 1000)]
print(f"turns {len(big)} of {len(rows)} lines; mean pre-queue {sum(map(pre,big))/max(1,len(big)):.0f}")
inc, slf, pres, calls = (collections.Counter() for _ in range(4))
for r in big:
    for k, (i, s, c) in r["c"].items():
        if k.startswith(a.prefix): inc[k] += i; slf[k] += s; pres[k] += 1; calls[k] += c
n = max(1, len(big))
for k, v in inc.most_common(a.top):
    print(f"  {k:24s} {pres[k]/n:5.0%} incl {v/n:7.0f} self {slf[k]/n:7.0f} percall {v/max(1,calls[k]):7.0f} calls {calls[k]/n:5.2f}")
