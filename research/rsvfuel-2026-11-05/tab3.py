"""X's p99 per state class: python tab3.py PKL"""
import sys, collections
import numpy as np
exec(open(__file__.replace("tab3.py", "common.py")).read())

recs = load(sys.argv[1])
cut = [r for r in recs if r["cut"] and not r["post_oof"] and r["X"] is not None and not r["opening"]]
print("cut non-opening", len(cut))


def cb(c):
    return "<=25" if c <= 25 else "26-64" if c <= 64 else "65-100" if c <= 100 else "101+"


def table(keyf, name):
    g = collections.defaultdict(list)
    for r in cut:
        g[keyf(r)].append(r)
    print("==", name)
    for k in sorted(g, key=str):
        xs = np.array([r["X"] for r in g[k]])
        res = np.array([r["reserve"] for r in g[k]])
        print(f"  {str(k):34s} n={len(xs):6d} X p50 {np.percentile(xs,50)/1e3:5.1f} p95 {np.percentile(xs,95)/1e3:5.1f} p99 {np.percentile(xs,99)/1e3:5.1f}"
              f" | reserve p50 {np.percentile(res,50)/1e3:5.1f} mean {res.mean()/1e3:5.1f} | X/chunk p99 {np.percentile(xs/np.maximum(r_ch(g[k]),1),99):6.0f}")


def r_ch(rs):
    return np.array([r["chunks"] for r in rs])


table(lambda r: (r["banks"], r["travel"] > 0, cb(r["chunks"])), "banks, dash ready, chunks")
table(lambda r: (r["banks"], r["cen"], r["apr"]), "banks, centre ready, approach ready")
table(lambda r: (r["banks"], r["zoned"]), "banks, zoned")
table(lambda r: (r["banks"], min(r["gsteps"] // 10, 5)), "banks, steps/10")
table(lambda r: (r["banks"], r["foes10"] > 0), "banks, foes within 10")
# within a chunk bucket, does X follow steps?
table(lambda r: (cb(r["chunks"]), min(r["gsteps"] // 15, 4)), "chunks, steps/15")
