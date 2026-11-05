"""cprof.py GAMES_DIR...: tabulate CREWPROF lines (crew pricing fuel by part) per farm loop, cut and finished."""
import sys, zipfile
from pathlib import Path

NAMES = ["crew_work", "plan_crew claimed", "may_beat block", "plan_crew crewable", "crew_allies build",
         "pc claimers+surv", "pc first mcd", "pc first share", "pc free list", "pc exp mcd", "pc exp share",
         "pc exp total", "pc home_surv | crewable raised", "share add/arrive | raised>best", "share sort/level | claimed op shared", "pc exp iters", "pc mcd hits", "pc mcd misses", "work_arrival", "cw camp_output", "pc mine arrival", "pc base pool", "pc exp join+output", "pc exp copy"]

rows = []
for d in sys.argv[1:]:
    for b in Path(d).rglob("*.repl26a"):
        with zipfile.ZipFile(b) as z:
            for n in z.namelist():
                if not n.endswith(".stdout"):
                    continue
                for line in z.read(n).decode(errors="replace").splitlines():
                    if not line.startswith("CREWPROF"):
                        continue
                    t = line.split()
                    if len(t) != 35 or t[3] != "cut":
                        continue
                    cut, bank = int(t[4]), int(t[6])
                    v, c = [], []
                    try:
                        for x in t[11:35]:
                            a, bb = x.split(":")
                            v.append(int(a)), c.append(int(bb))
                    except ValueError:
                        continue
                    if max(v) > 10**7:
                        continue
                    rows.append((cut, bank, v, c))

for cut in (1, 0):
    for bank in (0, 1):
        rs = [r for r in rows if r[0] == cut and r[1] == bank]
        if not rs:
            continue
        print(f"cut={cut} bank={bank}: loops {len(rs)}")
        for i, name in enumerate(NAMES):
            F = sum(r[2][i] for r in rs)
            N = sum(r[3][i] for r in rs)
            print(f"  {i:2d} {name:20s} per loop {F/len(rs):7.0f}  calls/loop {N/len(rs):5.2f}  per call {F/max(1,N):7.0f}")
