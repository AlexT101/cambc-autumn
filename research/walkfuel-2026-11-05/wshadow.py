#!/usr/bin/env python3
"""Kept-route misses an older found search (winst.py's shadow ring) would have answered: by miss reason and age,
with the search fuel that followed. python3 wshadow.py PKL"""
import sys, pickle, collections
import numpy as np

recs = [r for r in pickle.load(open(sys.argv[1], "rb")) if r["total"] < 10**6]
for name, sel in [("all", lambda r: True), ("cut nb", lambda r: r["cut"] and not r["bank"]), ("cut bank", lambda r: r["cut"] and r["bank"])]:
    rs = [r for r in recs if sel(r)]
    miss = collections.Counter()
    hit = collections.Counter()
    fuel_all = collections.Counter()
    fuel_hit = collections.Counter()
    ages = collections.Counter()
    for r in rs:
        ev = r["ev"]
        for i, e in enumerate(ev):
            if e[0] != "K" or e.count("/") != 4 or e[1] == "H":
                continue
            key = e[1]
            z = ev[i + 1] if i + 1 < len(ev) and ev[i + 1].startswith("Z") else None
            s = None
            for f in ev[i + 1:i + 4]:
                if f.startswith("S") and f.count("/") == 3:
                    s = int(f[2:].split("/")[2])
                    break
                if f.startswith("K"):
                    break
            if s is not None and s > 10**6:
                s = None
            miss[key] += 1
            fuel_all[key] += s or 0
            if z and z.count("/") == 1 and int(z[1:].split("/")[0]) >= 0:
                hit[key] += 1
                fuel_hit[key] += s or 0
                ages[int(z[1:].split("/")[0])] += 1
    n = len(rs)
    print(f"== {name}: {n} walks")
    for k in sorted(miss, key=lambda k: -miss[k]):
        print(f"   {k}: misses {miss[k]/n:.3f}/walk, search {fuel_all[k]/n:.0f}/walk; older hit {hit[k]/max(1,miss[k]):.1%}, saves {fuel_hit[k]/n:.0f}/walk")
    print("   ages:", sorted(ages.items()))
