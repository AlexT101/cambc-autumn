"""Evaluate fixed parameter sets: totals of simulated OOF, turn-order cuts, gain, and uncut turns newly below."""
import sys
import numpy as np
D = __file__.rsplit("/", 1)[0]
exec(open(D + "/common.py").read())
recs = load(sys.argv[1])
cut = [r for r in recs if r["cut"] and not r["opening"]]
unc = [r for r in recs if not r["cut"] and not r["opening"]]
END = 10000
SETS = {
    "fit4": {(0, 0): (18694, 30, 0.75), (0, 1): (23017, 30, 1.5), (1, 0): (20390, 0, 0.75), (1, 1): (24669, 40, 0.5)},
    "nb95": {(0, 0): (16397, 30, 0.75), (0, 1): (23017, 30, 1.5), (1, 0): (20390, 0, 0.75), (1, 1): (24669, 40, 0.5)},
    "nb93": {(0, 0): (15000, 30, 0.75), (0, 1): (21000, 30, 1.5), (1, 0): (20390, 0, 0.75), (1, 1): (24669, 40, 0.5)},
    "nb90": {(0, 0): (13500, 30, 0.75), (0, 1): (19500, 30, 1.5), (1, 0): (20390, 0, 0.75), (1, 1): (24669, 40, 0.5)},
    "nb93b98": {(0, 0): (15000, 30, 0.75), (0, 1): (21000, 30, 1.5), (1, 0): (21500, 0, 0.75), (1, 1): (26000, 40, 0.5)},
}


def rnew(r, P):
    p = P[(r["banks"], int(r["travel"] > 0))]
    if p is None:
        return r["reserve"]
    mn = p[0] == "min"
    a, b, d = p[1:] if mn else p
    v = END + a + b * r["chunks"] + d * r["chunks"] * (max(r["gsteps"], 0) + 16)
    return min(v, r["reserve"]) if mn else v


for name, P in SETS.items():
    order = oof = 0
    gain = 0.0
    o0 = sum(1 for r in cut if r["post_oof"])
    t0 = sum(1 for r in cut if not r["post_oof"] and r["T"] is not None and r["T"] < END)
    for r in cut:
        Rn = rnew(r, P)
        R = r["reserve"]
        Ln = r["L"] - R + Rn
        gain += R - Rn
        if r["post_oof"]:
            oof += Rn <= R or Ln < r["L"]
            continue
        if r["X"] is None:
            continue
        Tn = Ln - r["X"]
        oof += Tn < 0
        order += 0 <= Tn < END
    nb = sum(r["L"] < rnew(r, P) for r in unc) - sum(r["L"] < r["reserve"] for r in unc)
    nbg = np.mean([r["reserve"] - rnew(r, P) for r in cut if not r["banks"]])
    bg = np.mean([r["reserve"] - rnew(r, P) for r in cut if r["banks"]])
    print(f"{name:12s} gain nb {nbg:.0f} b {bg:.0f} oof {oof} (today {o0}) order {order} (today {t0}) gain {gain/len(cut):.0f} newly-below uncut {nb}")
