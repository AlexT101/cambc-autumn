"""Would a kept recall have landed? python3 recallcf.py EXTROOT/TAG [LINE]
Every round our Prism starts off spawn below LINE (default 0.32) of its health, not channelling a tribute, out of every
enemy's one-turn reach (hazard.py's burst model) with an enemy within 12: the standing counterfactual keeps the recall
from that tile. It lands if no enemy comes into reach of the tile in the next 4 rounds. Against what happened: death
within 12 rounds, and whether it stood on our spawn within 12."""
import collections, gzip, json, os, sys
from multiprocessing import Pool
from hazard import burst, cheb


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
    except Exception: return None
    line = float(sys.argv[2]) if len(sys.argv) > 2 else 0.32
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']
    pr = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; P = ch[p]; sp = mp['spawn'][us]; foes = [c for c in ch if team[c] != us]
    deaths = sorted(x['r'] for x in ev if x['k'] == 'death' and x['v'] == p)
    on = lambda i: P['alive'][i] and P['x'][i] is not None and sp['minX'] <= P['x'][i] <= sp['maxX'] and sp['minY'] <= P['y'][i] <= sp['maxY']

    def reached(i, tile):
        for e in foes:
            E = ch[e]
            if not E['alive'][i] or E['x'][i] is None or E['stun'][i]: continue
            x, st = burst(typ[e], cheb(tile, (E['x'][i], E['y'][i])), E['str'][i], E['foc'][i], E['cd0'][i], E['cd1'][i])
            if x > 0 or st: return True
        return False
    rows = []; last = -100
    for i in range(len(rounds) - 13):
        if not P['alive'][i] or P['x'][i] is None or on(i) or P['chan'][i] == 2: continue
        if P['hp'][i] >= line * P['maxHp'][i]: continue
        me = (P['x'][i], P['y'][i])
        near = [cheb(me, (ch[e]['x'][i], ch[e]['y'][i])) for e in foes if ch[e]['alive'][i] and ch[e]['x'][i] is not None]
        if not near or min(near) > 12 or reached(i, me): continue
        if rounds[i] - last < 5: continue  # one sample a recall's length
        last = rounds[i]
        lands = not any(reached(i + k, me) for k in range(1, 5))
        r = rounds[i]
        home = max(sp['minX'] - me[0], 0, me[0] - sp['maxX'], sp['minY'] - me[1], me[1] - sp['maxY'])
        rows.append((lands, any(r < q <= r + 12 for q in deaths), any(on(i + k) for k in range(1, 13)), home, min(near)))
    return rows


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    print(len(R), 'low-health starts out of reach with an enemy within 12')

    def line(name, S):
        if S: print(f'  {name:36s} {len(S):5d}  the recall would land {100 * sum(r[0] for r in S) / len(S):5.1f}%  actually: died within 12 rounds {100 * sum(r[1] for r in S) / len(S):5.1f}%, on spawn within 12 {100 * sum(r[2] for r in S) / len(S):5.1f}%')
    line('all', R)
    for lo, hi in ((0, 6), (6, 12), (12, 24), (24, 999)): line(f'spawn {lo}-{hi} away', [r for r in R if lo <= r[3] < hi])
    for lo, hi in ((0, 5), (5, 7), (7, 9), (9, 13)): line(f'nearest enemy {lo}-{hi} away', [r for r in R if lo <= r[4] < hi])
    S = [r for r in R if r[0]]
    line('recall would land', S); line('recall would not land', [r for r in R if not r[0]])
    line('would land, spawn 12+ away', [r for r in S if r[3] >= 12])
