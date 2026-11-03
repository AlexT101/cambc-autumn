"""Pairs SRCH lines of two bench runs whose replays are identical; per-phase fuel deltas (B - A).

    python3 research/aggro-2026-11-03/srch_pair.py replays/fuel/games/al-A replays/fuel/games/al-B
"""
import sys, zipfile, statistics as st
from pathlib import Path

PH = ("fuel", "read", "grow", "price", "act", "units")

def srch(d):
    out = {}
    for b in sorted(Path(d).glob("*/*.repl26a")):
        with zipfile.ZipFile(b) as z:
            for n in z.namelist():
                if not n.endswith(".stdout"): continue
                for j, l in enumerate(z.read(n).decode(errors="replace").replace("\x00", "").splitlines()):
                    if l.startswith("SRCH ") and " fuel " in l:
                        t = l.split()
                        try: out[(b.parent.name, n, j)] = {p: int(t[t.index(p) + 1]) for p in PH}
                        except (ValueError, IndexError): pass
    return out

a, b = srch(sys.argv[1]), srch(sys.argv[2])
keys = [k for k in a if k in b]
print(f"{len(keys)} paired searches ({len(a)} vs {len(b)})")
for p in PH:
    d = [b[k][p] - a[k][p] for k in keys]
    print(f"  {p:6s} A mean {st.mean(a[k][p] for k in keys):8.0f}  delta mean {st.mean(d):+7.0f} p50 {sorted(d)[len(d)//2]:+6d}  changed {sum(x != 0 for x in d)}")
d = [b[k]["units"] - a[k]["units"] for k in keys]
more = [k for k in keys if b[k]["units"] > a[k]["units"]]
same = [k for k in keys if b[k]["units"] == a[k]["units"]]
for name, ks in (("more units", more), ("same units", same)):
    if ks: print(f"  {name}: {len(ks)} searches, fuel delta mean {st.mean(b[k]['fuel'] - a[k]['fuel'] for k in ks):+.0f}, read {st.mean(b[k]['read'] - a[k]['read'] for k in ks):+.0f}")
