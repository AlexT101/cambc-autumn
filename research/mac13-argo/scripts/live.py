"""Interim win rates of running A/B batches: py live.py PATTERN (glob under replays/)."""
import glob, json, math, sys
for d in sorted(glob.glob('/home/ubuntu/wt/mac13-argo/replays/' + sys.argv[1])):
    try: r = json.load(open(d + '/results.json'))
    except Exception: continue
    m = [x for x in r['matches'] if x.get('winner') is not None]
    n = len(m); w = sum(1 for x in m if x['winner'] == 0)
    if not n: continue
    p = w / n; h = 1.96 * math.sqrt(p * (1 - p) / n)
    print(f"{d.split('mac13-argo-')[-1]:40s} {n:6d} {100*p:5.1f} +-{100*h:.1f}")
