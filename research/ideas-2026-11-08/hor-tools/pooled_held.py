"""Pooled held-out SPRT over several ab.py runs of one arm (in the order given), ab.py's LLR and bounds.
pooled_held.py --p0 P0 --p1 P1 --seed S RUN_A RUN_B ...  : RUN_A's pairs first (its own seeded order), then RUN_B's."""
import argparse, collections, json, os, random, sys  # run from the repo root
sys.path.insert(0, "tools"); import ab
def per_map(name):
    s = json.load(open(f"replays/ab/{name}/summary.json")); sides = collections.defaultdict(dict)
    for su in s["suites"]:
        try: r = json.load(open(os.path.join(su["batch"], "results.json")))
        except (OSError, ValueError): continue
        for m in r["matches"]:
            if "error" in m or "winner" not in m: continue
            sides[os.path.basename(os.path.realpath(m["map"]))][tuple(m["order"])] = int(m["winner"] == 0)
    return {k: sum(v.values()) / 2 for k, v in sides.items() if len(v) == 2}
ap = argparse.ArgumentParser(); ap.add_argument("--p0", type=float, default=0.5); ap.add_argument("--p1", type=float, default=0.5025)
ap.add_argument("--seed", type=int, default=0); ap.add_argument("--min-pairs", type=int, default=0); ap.add_argument("runs", nargs="+"); a = ap.parse_args()
lo, hi = ab.sprt_bounds(0.05, 0.05); seq = []
for i, r in enumerate(a.runs):
    pm = per_map(r); ks = sorted(pm); random.Random(a.seed + i).shuffle(ks); seq += [pm[k] for k in ks]
    print(f"{r}: {100*sum(pm.values())/len(pm):.2f}% of {2*len(pm)} games")
out, at = None, None; step = 64
for n in range(step, len(seq) + step, step):
    n = min(n, len(seq))
    if n < a.min_pairs: continue
    v = ab.llr(seq[:n], a.p0, a.p1)
    if v >= hi or v <= lo: out, at = ("H1" if v >= hi else "H0"), n; break
n = at or len(seq); s = seq[:n]; m = sum(s) / n
var = sum((x - m) ** 2 for x in s) / n; ci = 1.96 * (var / n) ** 0.5
print(json.dumps({"games": 2 * n, "win": round(100 * m, 2), "ci": [round(100 * (m - ci), 2), round(100 * (m + ci), 2)],
                  "llr": round(ab.llr(s, a.p0, a.p1), 3), "llr_all": round(ab.llr(seq, a.p0, a.p1), 3), "outcome": out or "undecided"}))
