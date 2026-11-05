"""What the tail of X is made of: python tail.py PKL"""
import sys, collections
import numpy as np
exec(open(__file__.replace("tail.py", "common.py")).read())

recs = load(sys.argv[1])
cut = [r for r in recs if r["cut"] and not r["opening"] and r["X"] is not None]
parts = "travel approach guard route zone tiles".split()
for b in (0, 1):
    for path in ("f", "b", "B"):
        rs = [r for r in cut if r["banks"] == b and path in first(r)]
        if not rs:
            continue
        X = np.array([r["X"] for r in rs])
        print(f"== banks={b} path={path} n={len(rs)} X p50 {np.percentile(X,50)/1e3:.1f} p95 {np.percentile(X,95)/1e3:.1f} p99 {np.percentile(X,99)/1e3:.1f}")
        for lo, hi in ((0, 50), (50, 90), (90, 99), (99, 100)):
            a, z = np.percentile(X, lo), np.percentile(X, hi)
            sel = [r for r in rs if a <= r["X"] <= z]
            s = "  ".join(f"{p} {np.mean([r['acc_'+p] for r in sel])/1e3:4.1f}" for p in parts)
            nr = np.mean([r["n_route"] for r in sel])
            other = np.mean([r["X"] - sum(r["acc_" + p] for p in parts if p != "guard") for r in sel])
            tv = np.mean([r["travel"] > 0 for r in sel])
            ch = np.mean([r["chunks"] for r in sel])
            ap = np.mean([r["apr"] for r in sel])
            print(f"   X p{lo}-{hi}: {s}  routes {nr:.2f} other {other/1e3:4.1f}  dash {tv:.2f} chunks {ch:.0f} apr {ap:.2f}")
