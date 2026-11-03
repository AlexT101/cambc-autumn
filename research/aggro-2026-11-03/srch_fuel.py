"""Strike-search fuel per bot across A/B batches, from debug builds' SRCH lines (combat/plan.cc debug_search).

    python3 research/aggro-2026-11-03/srch_fuel.py replays/batch-*-ab-NAME-*
"""
import sys, zipfile, statistics as st
from pathlib import Path

def lines(batches, botno):
    for d in batches:
        for b in sorted(Path(d).glob("*.repl26a")):
            order = b.stem.rsplit("-", 1)[1]
            team = "a" if (order == "12") == (botno == 1) else "b"
            with zipfile.ZipFile(b) as z:
                n = next((x for x in z.namelist() if x.endswith(f"team-{team}.stdout")), None)
                if n is None: continue
                for l in z.read(n).decode(errors="replace").replace("\x00", "").splitlines():
                    if l.startswith("SRCH ") and " fuel " in l:
                        t = l.split()
                        try: yield int(t[t.index("fuel") + 1]), int(t[t.index("nodes") + 1]), int(t[t.index("units") + 1])
                        except (ValueError, IndexError): pass

for botno, name in ((1, "CAND"), (2, "REF")):
    v = list(lines(sys.argv[1:], botno))
    f = sorted(x[0] for x in v)
    print(f"{name}: {len(v)} searches, fuel sum {sum(f)/1e9:.2f}G mean {st.mean(f):.0f} p50 {f[len(f)//2]} p90 {f[int(.9*len(f))]} "
          f"p99 {f[int(.99*len(f))]}; >50k {sum(x > 50000 for x in f)}; mean nodes {st.mean(x[1] for x in v):.0f}, units {st.mean(x[2] for x in v):.2f}")
