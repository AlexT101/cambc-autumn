"""Joint per-class quantiles under total constraints (OOF and turn-order cuts at or below today's)."""
import sys, itertools
import numpy as np
D = __file__.rsplit("/", 1)[0]
exec(open(D + "/sim.py").read().split("for qtl in")[0].replace("exec(open(__file__.replace(\"sim.py\", \"common.py\")).read())", "exec(open(D + \"/common.py\").read())"))
import os
KEY = os.environ.get("CLS", "")
def cls(r):
    k = (r["banks"], int(r["travel"] > 0))
    if "f" in KEY and not r["banks"]: k += (int(r["foes10"] > 0),)
    if "c" in KEY and not r["banks"]: k += (int(r["cen"] == 1),)
    return k
cut = [r for r in cut if r["apr"] >= 0]
QS = (93, 95, 97, 98, 99, 99.5)
classes = sorted(set(map(cls, cut)))
per = {}
for k in classes:
    rs = [r for r in cut if cls(r) == k]
    per[k] = []
    for qtl in QS:
        m, a, b, d = fit(rs, qtl)
        s = simulate(rs, model_reserve(rs, {k: (a, b, d)}))
        per[k].append((qtl, (a, b, d), s, len(rs)))
    s0 = dict(per[k][0][2]); s0.update(new_order=s0["now_order"], new_oof=s0["now_oof"], gain=0.0)
    per[k].append(("today", None, s0, len(rs)))
now_oof = sum(per[k][0][2]["now_oof"] for k in classes)
now_order = sum(per[k][0][2]["now_order"] for k in classes)
n = sum(per[k][0][3] for k in classes)
best = []
for combo in itertools.product(*[range(len(QS) + 1)] * len(classes)):
    oof = sum(per[k][i][2]["new_oof"] for k, i in zip(classes, combo))
    order = sum(per[k][i][2]["new_order"] for k, i in zip(classes, combo))
    gain = sum(per[k][i][2]["gain"] * per[k][i][3] for k, i in zip(classes, combo)) / n
    best.append((gain, oof, order, combo))
FORCE = len(sys.argv) > 2
print("today: oof", now_oof, "order", now_order)
for lim_order in (1.0, 1.25, 1.5):
    ok = [b for b in best if b[1] <= now_oof and b[2] <= lim_order * now_order and (not FORCE or b[3][0] == len(QS))]
    g = max(ok)
    print(f"order <= {lim_order}x: gain {g[0]:.0f} oof {g[1]} order {g[2]}", [(k, per[k][i][0], per[k][i][1] and tuple(round(float(x), 2) for x in per[k][i][1])) for k, i in zip(classes, g[3])])
