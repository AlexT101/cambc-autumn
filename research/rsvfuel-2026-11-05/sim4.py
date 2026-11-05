import sys
import numpy as np
D = __file__.rsplit("/", 1)[0]
exec(open(D + "/common.py").read())
P = {(0, 0): (18694, 30, 0.75), (0, 1): (23017, 30, 1.5), (1, 0): (20390, 0, 0.75), (1, 1): (24669, 40, 0.5)}
recs = load(sys.argv[1])
def rnew(r):
    a, b, d = P[(r["banks"], int(r["travel"] > 0))]
    return 10000 + a + b * r["chunks"] + d * r["chunks"] * (max(r["gsteps"], 0) + 16)
unc = [r for r in recs if not r["cut"] and not r["opening"]]
cut = [r for r in recs if r["cut"] and not r["opening"]]
a = sum(r["L"] < r["reserve"] for r in unc); b = sum(r["L"] < rnew(r) for r in unc)
print("uncut", len(unc), "L<R now", a, "L<Rnew", b)
for k in P:
    u = [r for r in unc if (r["banks"], int(r["travel"] > 0)) == k]
    c = [r for r in cut if (r["banks"], int(r["travel"] > 0)) == k]
    print(k, "uncut", len(u), "newly below", sum(r["L"] < rnew(r) for r in u) - sum(r["L"] < r["reserve"] for r in u), "cut", len(c),
          "mean R", np.mean([r["reserve"] for r in c]) / 1e3, "mean Rnew", np.mean([rnew(r) for r in c]) / 1e3)
