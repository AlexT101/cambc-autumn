"""SRCH line statistics (combat/plan.cc debug_search) from replays' stdout: by plan length and foes.

    python3 research/ideas-2026-11-05/fuel5-tools/srch.py DIR [DIR...]
"""
import collections, statistics, sys, zipfile
from pathlib import Path
rows = []
for d in sys.argv[1:]:
    for b in Path(d).rglob("*.repl26a"):
        side = b.parent.name.rsplit("-", 1)[-1]
        with zipfile.ZipFile(b) as z:
            for s in ([side] if side in "ab" else "ab"):
                for l in z.read(f"team-{s}.stdout").decode("utf-8", "replace").splitlines():
                    if l.startswith("SRCH "):
                        q = l.split()
                        f = dict(zip(q[3::2], q[4::2]))
                        r = {k: (int(v) if v.lstrip("-").isdigit() else v) for k, v in f.items()}
                        if all(isinstance(r.get(k), int) for k in ("fuel", "read", "grow", "price", "len", "nodes", "tiles", "foes", "units")): rows.append(r)
print("searches", len(rows), "fuel total", sum(r["fuel"] for r in rows))
tot = sum(r["fuel"] for r in rows)
def tab(key):
    c = collections.defaultdict(list)
    for r in rows: c[key(r)].append(r)
    for k in sorted(c, key=lambda k: -sum(r["fuel"] for r in c[k]))[:12]:
        rs = c[k]; f = sum(r["fuel"] for r in rs)
        print(f"  {str(k):28s} n {len(rs):7d} fuel {f/tot:6.1%} mean {f/len(rs):7.0f} read {statistics.fmean(r['read'] for r in rs):6.0f} grow {statistics.fmean(r['grow'] for r in rs):6.0f} price {statistics.fmean(r['price'] for r in rs):6.0f} nodes {statistics.fmean(r['nodes'] for r in rs):4.1f} tiles {statistics.fmean(r['tiles'] for r in rs):4.1f}")
print("by len"); tab(lambda r: min(r["len"], 3))
print("by foes, units"); tab(lambda r: (r["foes"], r["units"]))
print("by len0 x tiles"); tab(lambda r: (r["len"] == 0, min(r["tiles"], 9)))
