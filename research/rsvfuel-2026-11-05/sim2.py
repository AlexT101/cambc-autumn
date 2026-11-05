"""Per class: the lowest quantile whose simulated OOF and turn-order cuts stay at or below today's."""
import sys
import numpy as np
D = __file__.rsplit("/", 1)[0]
exec(open(D + "/sim.py").read().split("for qtl in")[0].replace("exec(open(__file__.replace(\"sim.py\", \"common.py\")).read())", "exec(open(D + \"/common.py\").read())"))
KEY = sys.argv[2] if len(sys.argv) > 2 else "bd"
def cls(r):
    k = (r["banks"], int(r["travel"] > 0))
    if "c" in KEY: k += (r["cen"],)
    if "z" in KEY: k += (r["zoned"],)
    return k
globals()["cls"] = cls
tot = {}
for k in sorted(set(map(cls, cut))):
    rs = [r for r in cut if cls(r) == k]
    if len(rs) < 300:
        print(k, len(rs), "too few: keep today's"); continue
    chosen = None
    for qtl in (95, 96, 97, 97.5, 98, 98.5, 99, 99.3, 99.5, 99.7, 99.8, 99.9):
        m, a, b, d = fit(rs, qtl)
        Rn = model_reserve(rs, {k: (a, b, d)})
        s = simulate(rs, Rn)
        ok = s["new_oof"] <= s["now_oof"] and s["new_order"] <= s["now_order"]
        if ok and chosen is None:
            chosen = (qtl, a, b, d, s)
    print(k, len(rs), chosen)
    if chosen: tot[k] = (len(rs), chosen[4]["gain"])
n = sum(v[0] for v in tot.values())
print("mean gain over chosen classes", sum(v[0]*v[1] for v in tot.values())/n, "of", n, "cut turns")
