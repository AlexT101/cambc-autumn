"""Tables over RSV records: python tab.py PKL [bot-substring]"""
import sys, pickle, collections
import numpy as np

recs = pickle.load(open(sys.argv[1], "rb"))
want = sys.argv[2] if len(sys.argv) > 2 else "rsv"
recs = [r for r in recs if want in r["bot"]]


def derive(r):
    ms = r["marks"]
    d = dict(ms[::-1])  # first occurrence wins
    first = {}
    for k, v in ms:
        first.setdefault(k, v)
    r["L"] = first.get("L")
    post_oof = any(ms[i][1] > ms[i - 1][1] for i in range(1, len(ms)))
    r["post_oof"] = post_oof
    if post_oof:
        # where: the first mark above its predecessor
        for i in range(1, len(ms)):
            if ms[i][1] > ms[i - 1][1]:
                r["oof_at"] = ms[i - 1][0] + ms[i][0]
                break
    T = first.get("T")
    r["X"] = r["L"] - T if T is not None and not post_oof else None
    r["T"] = T
    r["order"] = T - first["U"] if T is not None and "U" in first and not post_oof else None
    Q = first.get("Q")
    r["XQ"] = r["L"] - Q if Q is not None and not post_oof else None
    r["reserve"] = r["floor"] + r["lr"]


for r in recs:
    derive(r)


def q(xs, ps=(50, 90, 95, 99, 99.9)):
    xs = np.array([x for x in xs if x is not None])
    if len(xs) == 0:
        return "n=0"
    return f"n={len(xs):7d} mean {xs.mean()/1000:5.1f}k " + " ".join(f"p{p}={np.percentile(xs, p)/1000:5.1f}k" for p in ps) + f" max={xs.max()/1000:5.1f}k"


def show(name, rs):
    oof = sum(r["post_oof"] for r in rs)
    print(f"{name:40s} {q([r['X'] for r in rs])}  postOOF {oof} ({100*oof/max(1,len(rs)):.2f}%)")


print("records", len(recs))
cut = [r for r in recs if r["cut"]]
unc = [r for r in recs if not r["cut"]]
print("== X = L - T (loop exit to set_turn_order entry), excluding post-loop OOF turns")
show("all", recs)
show("cut", cut)
show("uncut", unc)
print("== reserve (floor+lr) on cut turns:", q([r["reserve"] for r in cut]))
print("== L on cut turns:", q([r["L"] for r in cut]))
print("== L - reserve on cut turns:", q([r["L"] - r["reserve"] for r in cut], (1, 10, 50, 90, 99)))
print("== turn order cost:", q([r["order"] for r in recs]))
print("== T (fuel at set_turn_order) on cut turns:", q([r["T"] for r in cut if not r["post_oof"]], (0.5, 1, 5, 10, 50)))
print("== L-Q :", q([r["XQ"] for r in cut]))
oofat = collections.Counter(r.get("oof_at") for r in recs if r["post_oof"])
print("post-loop OOF at", oofat.most_common(12))

for label, key in [("banks", "banks"), ("opening", "opening"), ("travel>0", "travel"), ("apr", "apr"), ("cen", "cen"),
                   ("zoned", "zoned"), ("canmove", "canmove"), ("best", "best"), ("gstate", "gstate"), ("shared", "shared"), ("help", "help")]:
    print(f"== by {label} (cut turns)")
    groups = collections.defaultdict(list)
    for r in cut:
        v = r[key]
        if key == "travel":
            v = v > 0
        groups[v].append(r)
    for v in sorted(groups, key=str):
        show(f"  {label}={v}", groups[v])

print("== by foes6 (cut turns)")
groups = collections.defaultdict(list)
for r in cut:
    groups[min(r["foes6"], 3)].append(r)
for v in sorted(groups):
    show(f"  foes6={v}", groups[v])
print("== by nearest foe (cut)")
groups = collections.defaultdict(list)
for r in cut:
    n = r["near"]
    groups["<=4" if n <= 4 else "5-6" if n <= 6 else "7-10" if n <= 10 else "11-20" if n <= 20 else ">20"].append(r)
for v in groups:
    show(f"  near {v}", groups[v])

print("== per-part costs on cut turns (mean / p99 of turns with the part)")
for part in "travel approach guard route zone order send queue tiles".split():
    xs = [r["acc_" + part] for r in cut if r["n_" + part] > 0 and not r["post_oof"]]
    print(f"  {part:9s} share {len(xs)/len(cut):.2f} {q(xs)}")
