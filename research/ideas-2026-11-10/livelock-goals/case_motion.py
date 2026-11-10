"""Summarize motion in the user's historical tribute window, from extracted rounds."""
import argparse, gzip, json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('rounds', type=Path)
ap.add_argument('--start', type=int, default=842)
ap.add_argument('--end', type=int, default=882)
a = ap.parse_args()
d = json.load(gzip.open(a.rounds))
rows = []
for c in d['champions']:
    if c['team'] != 0:
        continue
    xy = list(zip(c['x'], c['y']))
    ticks = range(a.start - 1, min(a.end, len(xy)))
    rows.append(dict(champion=c['id'],
        reversals=sum(xy[i] == xy[i-2] and xy[i] != xy[i-1] for i in ticks),
        stationary=sum(xy[i] == xy[i-1] for i in ticks),
        positions=len({xy[i] for i in ticks}),
        gems_start=c['gems'][a.start - 1], gems_end=c['gems'][a.end - 1]))
print(json.dumps(rows, indent=2))
