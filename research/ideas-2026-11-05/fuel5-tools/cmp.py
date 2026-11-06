"""bench.py JSONs, A vs B (same opponent): identical replays, total fuel, fuel on heavy turns (A >= 70k), turns > 100k.

    python3 research/ideas-2026-11-05/fuel5-tools/cmp.py A.json B.json
"""
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
key = lambda g: (g["map"], g["side"])
ga = {key(g): g for g in a["games"] if "error" not in g}; gb = {key(g): g for g in b["games"] if "error" not in g}
same = [k for k in sorted(ga.keys() & gb.keys()) if ga[k]["replay"] == gb[k]["replay"]]
print(f"identical {len(same)}/{len(ga.keys() & gb.keys())}", "" if len(same) == len(ga.keys() & gb.keys()) else
      "DIFFER " + " ".join(f"{m}-{s}" for m, s in sorted((ga.keys() & gb.keys()) - set(same))[:8]))
ta = [t for k in same for t in ga[k]["play"]]; tb = [t for k in same for t in gb[k]["play"]]
if ta and len(ta) == len(tb):
    h = [(x, y) for x, y in zip(ta, tb) if x >= 70000]
    pct = lambda x, y: f"{(y - x) / max(1, x):+.3%}"
    print(f"total {sum(ta)} -> {sum(tb)} {pct(sum(ta), sum(tb))}; heavy(>=70k) {len(h)} turns {pct(sum(x for x, _ in h), sum(y for _, y in h))};"
          f" >100k {sum(x > 100000 for x in ta)} -> {sum(y > 100000 for y in tb)}; cheaper {sum(y < x for x, y in zip(ta, tb))} dearer {sum(y > x for x, y in zip(ta, tb))}")
