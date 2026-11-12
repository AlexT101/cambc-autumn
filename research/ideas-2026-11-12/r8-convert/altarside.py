"""Our tribute channels of 21+ turn ends by how far inside our half their altar is (the enemy spawn's Chebyshev
distance to it minus ours), and by the deepest altar the map offers: py altarside.py EXT..."""
import gzip, json, sys
from pathlib import Path


def rows_of(ext):
    E = Path(ext)
    rows = []
    for r in json.loads((E / "index.json").read_text())["games"]:
        d = E / r["dir"]
        meta = json.loads((d / "meta.json").read_text())
        us = 0 if r["teams"][0].startswith("rc-") else 1
        mp = json.loads((E / "maps" / (r["mapHash"] + ".json")).read_text())
        team = {c["id"]: c["team"] for c in meta["champions"]}
        cen = [((s["minX"] + s["maxX"]) / 2, (s["minY"] + s["maxY"]) / 2) for s in mp["spawn"]]
        alt = mp["altars"]
        cheb = lambda a, c: max(abs(a[0] - c[0]), abs(a[1] - c[1]))
        side = lambda a: cheb(a, cen[1 - us]) - cheb(a, cen[us])
        best = max(side(a) for a in alt)
        open_ = {}
        for l in gzip.open(d / "events.jsonl.gz", "rt"):
            e = json.loads(l)
            k = e["k"]
            if k == "tribute_start" and team[e["a"]] == us and e["dur"] >= 21:
                open_[e["a"]] = e
            elif k in ("tribute_end", "tribute_cancel") and e["a"] in open_:
                s = open_.pop(e["a"])
                if k == "tribute_cancel" and e.get("cause") == "manual" and e["r"] - s["r"] <= 1:
                    continue
                at = s.get("at")
                apos = min(alt, key=lambda q: cheb(q, at))
                rows.append((len(alt), side(apos), best, k == "tribute_end", e.get("cause")))
            elif k == "death" and e["v"] in open_:
                open_.pop(e["v"])
    return rows


for ext in sys.argv[1:]:
    rows = rows_of(ext)
    print(f"== {ext}: {len(rows)} channels of 21+ turn ends, {100 * sum(x[3] for x in rows) / len(rows):.1f}% completed")
    for bl, bh in ((-99, 5), (5, 15), (15, 999)):
        for lo, hi in ((-999, 5), (5, 15), (15, 999)):
            b = [x for x in rows if x[0] > 1 and bl <= x[2] < bh and lo <= x[1] < hi]
            if b:
                print(f"  2+ altars, the map's deepest {bl}..{bh}, channel at {lo}..{hi}: n {len(b):4d}, completed {100 * sum(x[3] for x in b) / len(b):5.1f}%")
    b = [x for x in rows if x[0] == 1]
    print(f"  one altar: n {len(b)}, completed {100 * sum(x[3] for x in b) / max(1, len(b)):.1f}%")
