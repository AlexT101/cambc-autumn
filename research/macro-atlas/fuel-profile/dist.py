import sys, zipfile, collections
from pathlib import Path
d = sys.argv[1]
rows = []
for g in Path(d).iterdir():
    z = list(g.glob("*.repl26a")) if g.is_dir() else []
    if not z: continue
    s = zipfile.ZipFile(z[0]).read(f"team-{g.name[-1]}.stdout").decode("utf-8", "replace").replace("\x00", "")
    for line in s.splitlines():
        if not line.startswith("PROF "): continue
        p = line.split()
        if len(p) not in (17, 21): continue
        try: v = [tuple(map(int, x.split(":"))) for x in p[5:]]
        except ValueError: continue
        rows.append((int(p[3]), v))
def q(xs, f): xs = sorted(xs); return xs[int(f * (len(xs) - 1))] if xs else 0
for oof in (0, 1):
    R = [v for o, v in rows if o == oof]
    pf = [v[7][0] + v[8][0] + v[9][0] for v in R]; pc = [v[7][1] for v in R]; sim = [v[13][0] if len(v) > 13 else 0 for v in R]
    le = [v[0][0] for v in R]
    print("oof" if oof else "heavy", len(R))
    for name, xs in (("press fuel", pf), ("press computes", pc), ("press sim fuel", sim), ("lethal fuel", le)):
        print(f"  {name:16s} p50 {q(xs,.5)} p90 {q(xs,.9)} p99 {q(xs,.99)} max {max(xs)}  share>10k {sum(x>10000 for x in xs)/len(xs):.3f}")
import collections
for oof in (0, 1):
    R = [v for o, v in rows if o == oof and len(v) > 13 and v[13][0] > 0]
    c = collections.Counter(min(v[13][1], 5) for v in R)
    per = sorted(v[13][0] / v[13][1] for v in R)
    print("oof" if oof else "heavy", "turns with sims", len(R), "sims/turn", dict(sorted(c.items())), "per-sim p50", per[len(per)//2], "p90", per[int(.9*len(per))])
