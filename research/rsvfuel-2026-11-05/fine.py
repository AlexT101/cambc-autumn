import sys
import numpy as np
D = __file__.rsplit("/", 1)[0]
exec(open(D + "/common.py").read())
recs = load(sys.argv[1])
cut = [r for r in recs if r["cut"] and not r["opening"] and r["X"] is not None]
allr = [r for r in recs if not r["opening"] and r["X"] is not None]
parts = ("travel approach guard route zone tiles step_route see_revealed strike_enemy attack_camp cast_at_camp reset_attack "
         "home_stands ahead travel_dash heal shield ward lock strike_after cast_approach").split()
for name, rs in (("cut", cut), ("all", allr)):
    print("==", name, len(rs), "X mean", np.mean([r["X"] for r in rs]) / 1e3)
    for p in parts:
        xs = np.array([r["acc_" + p] for r in rs])
        n = np.array([r["n_" + p] for r in rs])
        print(f"  {p:13s} mean/turn {xs.mean()/1e3:5.2f}k  share {np.mean(n>0):.2f}  calls/turn {n.mean():.2f}  p99 {np.percentile(xs,99)/1e3:5.1f}k")
