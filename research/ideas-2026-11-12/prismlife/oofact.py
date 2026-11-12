"""Did the Prism act on its out-of-fuel turns? python3 oofact.py EXTROOT/TAG
For each turn the engine marks out of fuel (turn code 6): whether the Prism walked, attacked or cast in that round, by
context (an enemy champion hit it this round or the two before: fight; an enemy within 8: near; else calm), with what
followed: health lost over this round and the next, and death within 3 rounds. Other fight turns for comparison."""
import collections, gzip, json, os, sys
from multiprocessing import Pool


def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    except Exception: return None
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']
    pr = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; P = ch[p]; foes = [c for c in ch if team[c] != us]
    acted = collections.defaultdict(set); hit = collections.Counter(); deaths = set()
    for x in ev:
        if x.get('a') == p and x['k'] in ('move', 'attack', 'cast'): acted[x['r']].add(x['k'])
        if x['k'] in ('attack', 'cast') and team.get(x.get('a')) == 1 - us:
            for v, a in x.get('dmg') or []:
                if v == p: hit[x['r']] += a
        if x['k'] == 'death' and x['v'] == p: deaths.add(x['r'])
    rows = []
    for i, r in enumerate(rounds):
        t = P['turn'][i]
        if t not in (1, 2, 6): continue
        j = max(0, i - 1)
        me = (P['x'][j], P['y'][j]) if P['alive'][j] and P['x'][j] is not None else None
        if me is None: continue
        near = any(ch[e]['alive'][j] and ch[e]['x'][j] is not None and cheb(me, (ch[e]['x'][j], ch[e]['y'][j])) <= 8 for e in foes)
        fight = any(hit.get(q, 0) > 0 for q in (r - 2, r - 1, r))
        rows.append((t == 6, 'fight' if fight else 'near' if near else 'calm', bool(acted.get(r)), 'cast' in acted.get(r, ()), (hit.get(r, 0) + hit.get(r + 1, 0)) / max(1, P['maxHp'][j]),
                     any(q in deaths for q in (r, r + 1, r + 2, r + 3))))
    return rows


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    for ctx in ('fight', 'near', 'calm'):
        for oof in (True, False):
            S = [r for r in R if r[0] == oof and r[1] == ctx]
            if not S: continue
            print(f'{ctx:5s} {"out of fuel" if oof else "other turns":11s} {len(S):8d} turns  acted (walk, hit or cast) {100 * sum(r[2] for r in S) / len(S):5.1f}%  cast {100 * sum(r[3] for r in S) / len(S):5.1f}%  '
                  f'health lost this round and the next {sum(r[4] for r in S) / len(S):.3f}  dead within 3 rounds {100 * sum(r[5] for r in S) / len(S):.2f}%')
