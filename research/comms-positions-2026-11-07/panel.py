"""Paired panel: py panel.py CAND BASE MEMBER... (ab.py run names cm-panel-<bot>-<member>). Bot 0 is the A/B's CAND."""
import json, glob, sys, collections, math
cand, base, members = sys.argv[1], sys.argv[2], sys.argv[3:]
def per_map(name):
    s = collections.defaultdict(float)
    for f in glob.glob(f'replays/batch-*-ab-{name}-*/results.json'):
        for m in json.load(open(f))['matches']:
            if m.get('winner') is not None: s[m['map']] += 0.5 * (m['winner'] == 0)
    return s
pool = []
for mem in members:
    a, b = per_map(f'cm-panel-{cand}-{mem}'), per_map(f'cm-panel-{base}-{mem}')
    d = [a[k] - b[k] for k in a.keys() & b.keys()]
    n = len(d); mu = sum(d) / n; sd = math.sqrt(sum((x - mu) ** 2 for x in d) / (n - 1))
    print(f'{mem}: base {100*sum(b.values())/len(b):.1f} cand {100*sum(a.values())/len(a):.1f} diff {100*mu:+.2f} ±{196*sd/math.sqrt(n):.2f} ({n} maps)')
    pool += d
n = len(pool); mu = sum(pool) / n; sd = math.sqrt(sum((x - mu) ** 2 for x in pool) / (n - 1))
print(f'pooled diff {100*mu:+.2f} ±{196*sd/math.sqrt(n):.2f} ({n} maps)')
