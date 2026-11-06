"""Interim CAND win rate from ab.py suite logs: python3 wr.py NAME [NAME...] (replays/ab/NAME/*.log)."""
import math, re, sys
from pathlib import Path
for n in sys.argv[1:]:
    w = l = d = 0
    for f in Path(f"/home/ubuntu/cambc-autumn/replays/ab/{n}").glob("*.log"):
        for line in open(f, errors="replace"):
            m = re.search(r"bot (\d) wins", line)
            if m: w, l = (w + 1, l) if m.group(1) == "1" else (w, l + 1)
            elif "draw" in line.lower() and "A=" in line: d += 1
    t = w + l + d
    if t: p = (w + d / 2) / t; print(f"{n:24s} {t:6d} games  {100*p:.2f}% +- {196*math.sqrt(p*(1-p)/t):.2f}")
