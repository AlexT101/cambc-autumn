#!/usr/bin/env python3
"""Per turn (all walks of a farm turn after the loop): the parts' mean in the top tail vs all, by class.
python3 wtail.py PKL"""
import sys, pickle, collections
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from wan import PARTS

recs = pickle.load(open(sys.argv[1], "rb"))
turns = collections.defaultdict(lambda: dict(total=0, acc=collections.Counter(), n=0, searches=0, sfuel=0, chunks=0, entries="", cut=0, bank=0))
for r in recs:
    if r["total"] > 10**6:
        continue
    t = turns[(r["map"], r["round"], r["handle"])]
    t["total"] += r["total"]
    t["n"] += 1
    t["chunks"] = r["chunks"]
    t["cut"], t["bank"] = r["cut"], r["bank"]
    t["entries"] += r["entry"]
    for k, (f, c) in r["acc"].items():
        t["acc"][k] += f
    for e in r["ev"]:
        if e[0] == "S" and e.count("/") == 3:
            f = int(e[2:].split("/")[2])
            if f < 10**6:
                t["searches"] += 1
                t["sfuel"] += f
for name, sel in [("cut nb", lambda t: t["cut"] and not t["bank"]), ("cut bank", lambda t: t["cut"] and t["bank"]), ("all", lambda t: True)]:
    ts = [t for t in turns.values() if sel(t)]
    tot = np.array([t["total"] for t in ts])
    p95 = np.percentile(tot, 95)
    tail = [t for t in ts if t["total"] >= p95]
    print(f"== {name}: {len(ts)} turns, p50 {np.percentile(tot,50):.0f} p95 {p95:.0f} p99 {np.percentile(tot,99):.0f}; tail {len(tail)}")
    print(f"   walks/turn {np.mean([t['n'] for t in ts]):.2f} / tail {np.mean([t['n'] for t in tail]):.2f}; searches/turn {np.mean([t['searches'] for t in ts]):.2f} / tail {np.mean([t['searches'] for t in tail]):.2f}; search fuel {np.mean([t['sfuel'] for t in ts]):.0f} / tail {np.mean([t['sfuel'] for t in tail]):.0f}")
    print(f"   chunks p50 {np.percentile([t['chunks'] for t in ts],50):.0f} / tail {np.percentile([t['chunks'] for t in tail],50):.0f}")
    ent = collections.Counter()
    for t in tail:
        ent["".join(sorted(set(t["entries"])))] += 1
    print("   tail entry sets:", ent.most_common(8))
    for k, nm in PARTS.items():
        a = np.mean([t["acc"].get(k, 0) for t in ts])
        b = np.mean([t["acc"].get(k, 0) for t in tail])
        if b > 100:
            print(f"   {nm:20s} {a:7.0f} {b:7.0f}")
