"""obese.py EXTRACT_DIR...: how often a bag is provably untributable (V0: X(R), the smallest bag whose channel with a
Tribute emblem, b - floor(0.33 b), b = ceil(g/10), exceeds rounds left + 1), with walk 0."""
import collections, gzip, json, math, os, sys
def chan(g): b = max(1, math.ceil(g / 10)); return b - (int(0.33 * b) if g > 30 else 0)
def dead(g, r): return g > 0 and chan(g) > 2000 - r + 1
C = collections.Counter(); late = collections.Counter(); ex = []
for ext in sys.argv[1:]:
    ix = json.load(open(f'{ext}/index.json'))
    for g in ix['games']:
        if not g['ok']: continue
        d = f"{ext}/{g['dir']}"
        meta = json.load(open(f'{d}/meta.json'))
        R = json.load(gzip.open(f'{d}/rounds.json.gz'))
        name = {c['id']: c['name'] for c in meta['champions']}
        last = R['round'][-1]
        C['games'] += 1
        for t in (1500, 1800, 1900, 1950, 2000): late[t] += last >= t
        any_dead = any_dead_np = False; maxg = 0
        for c in R['champions']:
            for i, r in enumerate(R['round']):
                gm = c['gems'][i] or 0
                if c['alive'][i] and dead(gm, r):
                    any_dead = True; maxg = max(maxg, gm)
                    if name[c['id']] != 'Prism': any_dead_np = True
                    C['champ-rounds'] += 1
                    if name[c['id']] != 'Prism': C['champ-rounds non-Prism'] += 1
        C['games with a dead bag'] += any_dead; C['games with a non-Prism dead bag'] += any_dead_np
        if any_dead and len(ex) < 10: ex.append((g['dir'], last, maxg))
print(dict(C)); print('games reaching round', dict(late)); print(ex)
