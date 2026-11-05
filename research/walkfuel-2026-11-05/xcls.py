"""X (loop exit to the turn order) on cut, non-opening loops by reserve class and chunks, for several RSV pkls:
python3 xcls.py A.pkl [B.pkl ...]"""
import sys
import numpy as np
D = "/".join(__file__.split("/")[:-2]) + "/rsvfuel-2026-11-05"
exec(open(D + "/common.py").read())

runs = [(p, [r for r in load(p) if r["cut"] and not r["opening"]]) for p in sys.argv[1:]]
bk = [("<=25", 0, 25), ("26-64", 26, 64), ("65-100", 65, 100), ("101+", 101, 10**9), ("all", 0, 10**9)]
for banks in (0, 1):
    for tv in (0, 1):
        print(f"== banks {banks} dash {tv}: p50 / p95 / p99 of X, k")
        for name, lo, hi in bk:
            row = []
            for p, rs in runs:
                xs = np.array([r["X"] for r in rs if r["banks"] == banks and (r["travel"] > 0) == tv and lo <= r["chunks"] <= hi and r["X"] is not None])
                row.append(f"n={len(xs):6d} {np.percentile(xs, 50)/1e3:5.1f} {np.percentile(xs, 95)/1e3:5.1f} {np.percentile(xs, 99)/1e3:5.1f}" if len(xs) else "n=0")
            print(f"  {name:7s} " + "   |   ".join(row))
