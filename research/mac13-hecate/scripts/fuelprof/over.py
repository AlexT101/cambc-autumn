"""over.py BENCH.json...: play-turn (from round 2) mean, p99, max, >100k, >200k per bench JSON."""
import json, sys
for p in sys.argv[1:]:
    d = json.load(open(p)); t = sorted(x for g in d['games'] for x in g['play'])
    n = len(t)
    print(f"{p.rsplit('/', 1)[-1]:20s} turns {n} mean {sum(t) // n} p99 {t[int(0.99 * n)]} max {t[-1]} >100k {sum(x > 100000 for x in t)} >200k {sum(x > 200000 for x in t)}")
