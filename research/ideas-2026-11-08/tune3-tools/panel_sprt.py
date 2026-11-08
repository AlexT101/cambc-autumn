"""Sequential panel test, paired by map and pooled over members (TEST-STANDARD.md), with ab.py's LLR.

    panel_sprt.py --p0 0.50 --p1 0.5025 --seed S --direct CAND_vs_BASE_RUN \
        --paired CAND_vs_M1_RUN:BASE_vs_M1_RUN [--paired ...]

Runs are ab.py names (replays/ab/NAME/summary.json). A map's unit score is CAND's mean over its two sides for the
direct member (CAND-td against BASE-td), and 0.5 + CAND's mean - BASE's mean on the same map for a paired member.
Maps are taken in a fixed shuffled order (seed), every member's unit for a map together, and the test stops at the
first crossing of ab.py's bounds (alpha = beta = 0.05), so the full runs are a sequence read in a fixed order.
"""
import argparse, collections, json, math, os, random, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools"))
import ab  # noqa: E402


def per_map(name):
    s = json.load(open(f"replays/ab/{name}/summary.json"))
    sides = collections.defaultdict(dict)
    for su in s["suites"]:
        try:
            r = json.load(open(os.path.join(su["batch"], "results.json")))
        except (OSError, ValueError):
            continue
        for m in r["matches"]:
            if "error" in m or "winner" not in m:
                continue
            sides[os.path.basename(os.path.realpath(m["map"]))][tuple(m["order"])] = int(m["winner"] == 0)
    return {k: sum(v.values()) / 2 for k, v in sides.items() if len(v) == 2}


ap = argparse.ArgumentParser()
ap.add_argument("--p0", type=float, default=0.50)
ap.add_argument("--p1", type=float, default=0.5025)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--direct", action="append", default=[])
ap.add_argument("--paired", action="append", default=[])
a = ap.parse_args()
units = collections.defaultdict(list)  # map -> unit scores
members = {}
for d in a.direct:
    pm = per_map(d)
    members[d] = (100 * (sum(pm.values()) / len(pm) - 0.5), len(pm))
    for k, v in pm.items():
        units[k].append(v)
for p in a.paired:
    c, b = p.split(":")
    pc, pb = per_map(c), per_map(b)
    ks = pc.keys() & pb.keys()
    ds = [pc[k] - pb[k] for k in ks]
    mu = sum(ds) / len(ds)
    sd = math.sqrt(sum((x - mu) ** 2 for x in ds) / max(1, len(ds) - 1))
    members[c] = (100 * mu, len(ds), 196 * sd / math.sqrt(len(ds)))
    for k in ks:
        units[k].append(0.5 + pc[k] - pb[k])
order = sorted(units)
random.Random(a.seed).shuffle(order)
lo, hi = ab.sprt_bounds(0.05, 0.05)
scores, outcome, at = [], None, None
for k in order:
    scores += units[k]
    v = ab.llr(scores, a.p0, a.p1)
    if outcome is None and (v >= hi or v <= lo):
        outcome, at = ("H1" if v >= hi else "H0"), len(scores)
for m, r in members.items():
    print(f"{m}: {r[0]:+.2f}" + (f" ±{r[2]:.2f}" if len(r) > 2 else "") + f" ({r[1]} maps)")
mean = sum(scores) / len(scores)
print(json.dumps({"units": len(scores), "pooled_pts": round(100 * (mean - 0.5), 3), "llr_final": round(ab.llr(scores, a.p0, a.p1), 3),
                  "bounds": [round(lo, 3), round(hi, 3)], "outcome": outcome, "decided_at_units": at,
                  "p0": a.p0, "p1": a.p1}))
