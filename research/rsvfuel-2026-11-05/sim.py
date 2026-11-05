"""Fit X's quantile per class as a + b*chunks + d*chunks*layers, and simulate the new reserve:
python sim.py PKL"""
import sys, collections
import numpy as np
exec(open(__file__.replace("sim.py", "common.py")).read())

recs = load(sys.argv[1])
cut = [r for r in recs if r["cut"] and not r["opening"]]
print("cut non-opening", len(cut), "post-OOF", sum(r["post_oof"] for r in cut))
END = 10000


def cls(r):
    return (r["banks"], int(r["travel"] > 0))


def arrays(rs):
    c = np.array([r["chunks"] for r in rs], float)
    lay = np.array([max(r["gsteps"], 0) + 16 for r in rs], float)
    X = np.array([r["X"] if r["X"] is not None else r["L"] + 1 for r in rs], float)
    L = np.array([r["L"] for r in rs], float)
    R = np.array([r["reserve"] for r in rs], float)
    oof = np.array([r["post_oof"] for r in rs])
    return c, lay, X, L, R, oof


def fit(rs, qtl):
    c, lay, X, L, R, oof = arrays([r for r in rs if not r["post_oof"]])
    best = None
    for b in np.arange(0, 301, 10):
        for d in np.arange(0, 4.01, 0.25):
            base = b * c + d * c * lay
            a = np.percentile(X - base, qtl)
            m = (a + base).mean()
            if best is None or m < best[0]:
                best = (m, a, b, d)
    return best


def model_reserve(rs, params):
    c, lay, X, L, R, oof = arrays(rs)
    out = np.zeros(len(rs))
    for i, r in enumerate(rs):
        a, b, d = params[cls(r)]
        out[i] = END + a + b * c[i] + d * c[i] * lay[i]
    return out


def simulate(rs, Rn):
    c, lay, X, L, R, oof = arrays(rs)
    Ln = L - R + Rn
    Tn = Ln - X
    T = L - X
    res = dict(
        now_order=int(((T < END) & ~oof).sum()), now_oof=int(oof.sum()),
        new_order=int(((Tn < END) & (Tn >= 0) & ~(oof & (Rn <= R))).sum()),
        new_oof=int(((Tn < 0) & ~oof).sum() + (oof & (Rn <= R)).sum() + (oof & (Rn > R) & (Ln - L < 0)).sum()),
        gain=float((R - Rn).mean()), gain_pos=float(np.mean(R - Rn > 5000)), worse=float(np.mean(Rn > R)))
    return res


for qtl in (98, 99, 99.5, 99.8):
    params = {}
    for k in sorted(set(map(cls, cut))):
        rs = [r for r in cut if cls(r) == k]
        m, a, b, d = fit(rs, qtl)
        params[k] = (a, b, d)
    Rn = model_reserve(cut, params)
    s = simulate(cut, Rn)
    print(f"q{qtl}: " + " ".join(f"{k}:a={v[0]:.0f},b={v[1]:.0f},d={v[2]:.2f}" for k, v in params.items()))
    print("     ", s)
    for k in sorted(params):
        idx = [i for i, r in enumerate(cut) if cls(r) == k]
        s = simulate([cut[i] for i in idx], Rn[idx])
        print("     ", k, len(idx), s)
