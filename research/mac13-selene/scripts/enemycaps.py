import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT, CAND = sys.argv[1], sys.argv[2]
def game(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); mp = json.load(open(os.path.join(d, meta['mapFile'])))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    except Exception: return None
    names = [t['name'] for t in meta['teams']]; G = {g['id']: g for g in mp['groups']}
    n = len(R['round']); rix = {r: i for i, r in enumerate(R['round'])}
    dead = [[0] * n, [0] * n]
    for c in R['champions']:
        for i, a in enumerate(c['alive']):
            if not a: dead[c['team']][i] += 1
    res = Counter()
    for t in (0, 1):
        who = 'cand' if CAND in names[t] else 'ref'
        for i in range(n): res[(who, min(dead[1 - t][i], 1), 'rounds')] += 1
    for e in ev:
        if e['k'] != 'capture': continue
        t = e['team']; i = rix.get(e['r'])
        if i is None: continue
        who = 'cand' if CAND in names[t] else 'ref'; sd = G[e['g']]['side']
        z = 'enemy' if sd == 1 - t else 'own' if sd == t else 'mid'
        res[(who, min(dead[1 - t][i], 1), z)] += sum(s[1] for s in e['shares'])
    return res
def main():
    dirs = [os.path.join(ROOT, x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, x)) and x != 'maps']
    tot = Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game, dirs, chunksize=4):
            if r: tot.update(r)
    for who in ('cand', 'ref'):
        for k in (0, 1):
            r = tot[(who, k, 'rounds')] or 1
            print(who, '0 dead' if k == 0 else '1+ dead', 'team-rounds', r, ' captured gems /100 team-rounds: own %.1f mid %.1f enemy %.1f' % tuple(100 * tot[(who, k, z)] / r for z in ('own', 'mid', 'enemy')))
if __name__ == '__main__': main()
