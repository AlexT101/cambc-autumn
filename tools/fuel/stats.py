"""Headline numbers of bench.py JSONs side by side: mean, p99, max, over 100k, round 1 mean, OOF and shortcuts.

    py tools/fuel/stats.py BASE.json CAND.json [CAND2.json ...]
"""
import json
import sys
from collections import Counter

rows = []
for p in sys.argv[1:]:
    d = json.load(open(p))
    sc = Counter()
    oof = 0
    for g in d["games"]:
        sc.update(g.get("shortcuts") or {})
        oof += g.get("out_of_fuel") or 0
    rows.append((p.rsplit("/", 1)[-1], d["all"], d["round1"], oof, sc))
keys = [k for k, _ in rows[0][4].most_common(12)]
print(f"{'':28s} {'mean':>7s} {'p99':>7s} {'max':>7s} {'>100k':>6s} {'r1mean':>7s} {'OOF':>5s} " + " ".join(f"{k[:14]:>14s}" for k in keys))
for name, a, r1, oof, sc in rows:
    print(f"{name[:28]:28s} {a['mean']:7d} {a['p99']:7d} {a['max']:7d} {a['over_100k']:6d} {r1['mean']:7d} {oof:5d} "
          + " ".join(f"{sc.get(k, 0):14d}" for k in keys))
