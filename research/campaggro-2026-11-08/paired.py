"""Rare gate: CAND's results on the games where it fired (FIRED list of replay paths), paired with the same map and
seating in a base mirror batch. Usage: python3 paired.py CAND_BATCH MIRROR_BATCH FIRED_LIST"""
import json, os, sys, math
def res(b):
    out = {}
    for m in json.load(open(b + '/results.json'))['matches']:
        if 'winner' in m: out[(os.path.basename(m['map']), tuple(m['order']))] = (int(m['winner'] == m['order'].index(0)) if False else int(m['winner'] == 0))
    return out, {os.path.basename(m['replay']): (os.path.basename(m['map']), tuple(m['order'])) for m in json.load(open(b + '/results.json'))['matches']}
c, cr = res(sys.argv[1]); b, _ = res(sys.argv[2])
fired = [os.path.basename(l.strip()) for l in open(sys.argv[3]) if l.strip()]
d = []
for f in fired:
    k = cr.get(f)
    if k in c and k in b: d.append(c[k] - b[k])
n = len(d); m = sum(d) / n; sd = math.sqrt(sum((x - m) ** 2 for x in d) / max(1, n - 1))
print(f'fired games {n}: cand {sum(c[cr[f]] for f in fired if cr.get(f) in c and cr.get(f) in b)/n:.3f} mirror {sum(b[cr[f]] for f in fired if cr.get(f) in c and cr.get(f) in b)/n:.3f} '
      f'delta {m:+.3f} +- {1.96*sd/math.sqrt(n):.3f}; flips +{d.count(1)} -{d.count(-1)}')
