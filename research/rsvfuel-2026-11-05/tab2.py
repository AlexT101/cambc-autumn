"""Segments and estimate fit: python tab2.py PKL"""
import sys, pickle, collections
import numpy as np
sys.argv += []
exec(open(__file__.replace("tab2.py", "common.py")).read())

recs = load(sys.argv[1])
cut = [r for r in recs if r["cut"] and not r["post_oof"]]
print("cut turns (no post OOF)", len(cut))


def seg(r, a, b):
    f = first(r)
    if a in f and b in f:
        return f[a] - f[b]
    return None


print("== segments on cut turns")
for a, b in [("L", "P"), ("P", "f"), ("P", "F"), ("L", "B"), ("L", "b"), ("B", "A"), ("b", "A"), ("f", "A"), ("F", "A"), ("A", "T"), ("U", "D"), ("D", "Q")]:
    print(f"  {a}->{b}", q([seg(r, a, b) for r in cut]))

print("== route actual / se (cut turns with a route)")
rs = [r for r in cut if r["n_route"] > 0 and r["se"] > 0]
ratio = [r["acc_route"] / r["se"] for r in rs]
print("  ratio", q([x * 1000 for x in ratio]), "(x1000)")
print("  route calls", collections.Counter(min(r["n_route"], 5) for r in rs))
print("== travel actual by dash-ready (cut turns)")
for tv in (0, 1):
    xs = [r["acc_travel"] for r in cut if (r["travel"] > 0) == tv]
    print(f"  travel_ready={tv}", q(xs))
print("== X by chunks bucket (cut, nonbanking / banking)")
for b in (0, 1):
    g = collections.defaultdict(list)
    for r in cut:
        if r["banks"] != b or r["opening"]:
            continue
        c = r["chunks"]
        g["<=25" if c <= 25 else "26-64" if c <= 64 else "65-100" if c <= 100 else "101-169"].append(r)
    for k in ("<=25", "26-64", "65-100", "101-169"):
        if k in g:
            print(f"  banks={b} chunks {k:8s}", q([r["X"] for r in g[k]]), " reserve", q([r["floor"] + r["lr"] for r in g[k]], (50,)))
print("== X - (se + travel + wr) (cut, non-opening)")
xs = [r["X"] - (r["se"] + r["travel"] + r["wr"]) for r in cut if not r["opening"] and r["X"] is not None]
print("  ", q(xs, (50, 90, 95, 99, 99.9)))
xs = [r["X"] - (r["se"] + r["travel"]) for r in cut if not r["opening"] and r["X"] is not None]
print("  X-(se+travel)", q(xs, (50, 90, 95, 99, 99.9)))
xs = [r["X"] - (r["se"]) for r in cut if not r["opening"] and r["X"] is not None]
print("  X-se", q(xs, (50, 90, 95, 99, 99.9)))
xs = [r["X"] / r["se"] for r in cut if not r["opening"] and r["se"] and r["X"] is not None]
print("  X/se x1000", q([x * 1000 for x in xs], (50, 90, 95, 99, 99.9)))
print("== cuts fired after the loop (cut turns)")
c = collections.Counter(x for r in cut for x in r["cuts"] if x != "farm-partial-evaluation")
print("  ", c.most_common(15))
