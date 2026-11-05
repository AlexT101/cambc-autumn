"""Refit a class's flat term at the quantile today's term sits at on the base run:
python3 refit.py BASE.pkl CAND.pkl BANKS DASH A B D
(A, B, D: today's a, b per chunk, d per chunk-layer). Prints the quantile, the refitted a and the simulated
post-loop OOF and turn-order shortfalls (sim.py's simulate) on the candidate run at a few a."""
import sys
import numpy as np
D_ = "/".join(__file__.split("/")[:-2]) + "/rsvfuel-2026-11-05"
D = D_
exec(open(D + "/sim.py").read().split("for qtl in")[0].replace("exec(open(__file__.replace(\"sim.py\", \"common.py\")).read())", "exec(open(D + \"/common.py\").read())").replace("recs = load(sys.argv[1])", "recs = []"))

base_p, cand_p = sys.argv[1], sys.argv[2]
banks, dash = int(sys.argv[3]), int(sys.argv[4])
A, B, Dd = float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7])


def rows(p):
    return [r for r in load(p) if r["cut"] and not r["opening"] and r["banks"] == banks and (r["travel"] > 0) == dash]


def resid(rs):
    c, lay, X, L, R, oof = arrays([r for r in rs if not r["post_oof"]])
    return X - (B * c + Dd * c * lay)


rb, rc = rows(base_p), rows(cand_p)
# Today the loop reserve includes the floor: the logged floor + lr counts it twice.
for r in rb + rc:
    r["reserve"] = r["lr"]
eb, ec = resid(rb), resid(rc)
qstar = 100.0 * np.mean(eb <= A)
print(f"class banks={banks} dash={dash}: base n={len(rb)} cand n={len(rc)}; a={A:.0f} sits at q{qstar:.2f} on base")
a_new = np.percentile(ec, qstar)
print(f"refit at q{qstar:.2f} on cand: a={a_new:.0f} (base's own refit {np.percentile(eb, qstar):.0f})")
for name, rs in (("base", rb), ("cand", rc)):
    c, lay, X, L, R, oof = arrays(rs)
    for a in (A, a_new, A - 500, A - 1000, A - 1500, A - 2000):
        Rn = END + a + B * c + Dd * c * lay
        s = simulate(rs, Rn)
        print(f"  {name} a={a:6.0f}: oof {s['now_oof']} -> {s['new_oof']}, order {s['now_order']} -> {s['new_order']}, gain {s['gain']:.0f} (vs logged reserve)")
