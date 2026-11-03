"""Mean inclusive/self fuel and calls of every census component on a bot's CEN turns that hold a given component
(>= 1k inclusive), split by out-of-fuel or not: what a branch spends its fuel on.

    python3 cen_within.py DIR COMPONENT [DIR2]   # DIR: split_sides.py output
"""
import collections
import sys

sys.path.insert(0, "/home/ubuntu/cambc-autumn/tools/fuel/census")
from census import load  # noqa: E402


def table(d, comp):
    rows = [r for r in load([d]) if r["c"].get(comp, (0,))[0] >= 1000]
    out = {}
    for oof in (True, False):
        rs = [r for r in rows if r["oof"] == oof]
        tot = collections.defaultdict(lambda: [0, 0, 0])
        for r in rs:
            for k, v in r["c"].items():
                for i in range(3):
                    tot[k][i] += v[i]
        out[oof] = (len(rs), {k: [x / max(1, len(rs)) for x in v] for k, v in tot.items()})
    return out


a = table(sys.argv[1], sys.argv[2])
b = table(sys.argv[3], sys.argv[2]) if len(sys.argv) > 3 else None
for oof in (True, False):
    n, t = a[oof]
    print(f"\n== {'OOF' if oof else 'finished'}: {n} turns" + (f" vs {b[oof][0]}" if b else ""))
    keys = sorted(t, key=lambda k: -t[k][0])[:40]
    for k in keys:
        line = f"  {k:22s} incl {t[k][0]:9.0f} self {t[k][1]:8.0f} calls {t[k][2]:8.1f}"
        if b:
            u = b[oof][1].get(k, [0, 0, 0])
            line += f"   | incl {u[0]:9.0f} self {u[1]:8.0f} calls {u[2]:8.1f}"
        print(line)
