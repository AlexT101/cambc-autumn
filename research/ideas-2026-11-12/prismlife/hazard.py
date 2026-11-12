"""The Prism's death hazard against the burst the enemies near it could deal.

    python3 hazard.py EXTROOT/TAG

For every round our Prism starts alive, off its spawn, with an enemy champion within 6: B1 is the most the living
enemies could deal to its tile in one turn each, by the rules' action allowances from their type, distance, Strength,
Focus and cooldowns (terrain, sight and items ignored); B1 / health is the burst share. Printed: deaths within 1, 3 and
6 rounds by burst share, by how many enemies reach, and by the share once the enemies have each walked a step (B2);
and for the deaths, how many rounds before the end each share was first crossed.
"""
import collections, gzip, json, os, pickle, sys
from multiprocessing import Pool


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def burst(typ, d, s, f, c0, c1, hpshare=1.0):
    """Most damage in one turn at Chebyshev distance d; (damage, stuns)."""
    r0, r1 = c0 <= 0, c1 <= 0
    best = (0.0, False)

    def take(x, st=False):
        nonlocal best
        if x > best[0] or (x == best[0] and st and not best[1]): best = (x, st)
    melee = typ in ('Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Heart of Ruin', 'Issac')
    if melee:
        if d <= 2: take(s)
    else:
        if d <= 3: take(s)
    if typ == 'Ryth':
        if r1 and d <= 2: take(2 * s)
        if r0 and d <= 5: take(f + (s if d <= 1 else 0), True)
    elif typ == 'Vesper Vale':
        if r0 and d <= 3: take(2 * s)
        if r0 and d == 4: take(s)
        if r1 and d <= 5: take(s)
    elif typ == 'Prism':
        if r0 and d <= 4: take(1.5 * f + (s if d <= 3 else 0), True)
        if r1 and d <= 5: take(f + (s if d <= 3 else 0))
    elif typ == 'Stellar':
        if r0 and d <= 4: take(2 * f + (s if d <= 3 else 0))
        if r1 and d <= 5: take(1.4 * f + (s if d <= 3 else 0))
    elif typ in ('Vendetta', 'Issac'):
        if r0 and d <= 2: take(2 * s)
        if r1 and d <= 4: take(s)
    elif typ == 'Marcella':
        if r0 and d <= 2: take(2 * s, True)
        if r1 and d <= 4: take(2 * f + (s if d <= 1 else 0))
    elif typ == 'Tavi':
        if r0 and d <= 3: take(2 * s)
        if r0 and d == 4: take(s)
        if r1 and d <= 4: take(1.6 * f + (s if d <= 3 else 0), True)
    elif typ == 'Willow':
        if r1 and d <= 3: take(2 * s)
        if r1 and d == 4: take(s)
    elif typ == 'Ren':
        if r0 and d <= 4: take(1.1 * f + (s if d <= 1 else 0), True)
        if r1 and d <= 4: take(s)
    elif typ == 'Varg':
        if r0 and d <= 2: take(2 * s)
    elif typ == 'Heart of Ruin':
        k = 1 + 0.5 * (1 - hpshare)
        best = (best[0] * k, best[1])
        if r1 and d <= 4: take((1.5 * f + s) * k, True)
    elif typ == 'Cassi':
        if r0 and d <= 4: take(2 * f + (s if d <= 3 else 0))
        if r1 and d <= 5: take(s if d <= 4 else 0, True)
    return best


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
    except Exception as e:
        sys.stderr.write(f'{d}: {e!r}\n')
        return None
    names = [t['name'] for t in meta['teams']]
    us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}
    rounds = R['round']
    prisms = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    if not prisms: return []
    p = prisms[0]; P = ch[p]
    sp = mp['spawn'][us]
    foes = [c for c in ch if team[c] != us]; mates = [c for c in ch if team[c] == us and c != p]
    deaths = sorted(x['r'] for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is not None)
    rows = []
    for i in range(len(rounds) - 1):
        r = rounds[i] + 1  # the state at the end of round[i] is the start of r
        if not P['alive'][i] or P['x'][i] is None: continue
        me = (P['x'][i], P['y'][i])
        if sp['minX'] <= me[0] <= sp['maxX'] and sp['minY'] <= me[1] <= sp['maxY']: continue
        b1 = b2 = 0.0; n1 = n2 = 0; near = 0; stun1 = False
        for e in foes:
            E = ch[e]
            if not E['alive'][i] or E['x'][i] is None: continue
            dd = cheb(me, (E['x'][i], E['y'][i]))
            if dd > 8: continue
            near += dd <= 6
            if E['stun'][i]: continue
            hs = E['hp'][i] / max(1, E['maxHp'][i])
            x, st = burst(typ[e], dd, E['str'][i], E['foc'][i], E['cd0'][i], E['cd1'][i], hs)
            if x > 0 or st: b1 += x; n1 += 1; stun1 |= st
            y, _ = burst(typ[e], dd - 1, E['str'][i], E['foc'][i], E['cd0'][i] - 1, E['cd1'][i] - 1, hs)
            if y > 0: b2 += y; n2 += 1
        if near == 0: continue
        na = sum(1 for c in mates if ch[c]['alive'][i] and ch[c]['x'][i] is not None and cheb(me, (ch[c]['x'][i], ch[c]['y'][i])) <= 6)
        hp = P['hp'][i] + P['shield'][i]
        nd = next((q - r for q in deaths if q >= r), 999)
        rows.append((b1 / max(1, hp), b2 / max(1, hp), n1, n2, nd, P['hp'][i] / max(1, P['maxHp'][i]), stun1, na, P['gems'][i], P['chan'][i]))
    return rows


def main():
    root = sys.argv[1]
    c = root.rstrip('/') + '.hazard.pkl'
    if os.path.exists(c): rows = pickle.load(open(c, 'rb'))
    else:
        dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
        with Pool(24) as pool:
            rows = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
        pickle.dump(rows, open(c, 'wb'))
    nd = sum(1 for r in rows if r[4] == 0)
    print(f'{root}: {len(rows)} Prism rounds with an enemy within 6, off spawn; deaths to champions {nd}')

    def tab(name, key, order):
        g = collections.defaultdict(list)
        for r in rows: g[key(r)].append(r)
        print(f'\n{name}')
        for k in order:
            s = g.get(k)
            if not s: continue
            d1 = sum(1 for r in s if r[4] <= 0); d3 = sum(1 for r in s if r[4] <= 2); d6 = sum(1 for r in s if r[4] <= 5)
            print(f'  {str(k):14s} {len(s):8d} rounds ({100 * len(s) / len(rows):5.1f}%)  die this round {100 * d1 / len(s):5.2f}%  within 3 {100 * d3 / len(s):5.2f}%  within 6 {100 * d6 / len(s):5.2f}%   deaths this round {d1} ({100 * d1 / max(1, nd):.0f}%)')
    cuts = [0.001, 0.25, 0.5, 0.75, 1.0, 1.5]
    b = lambda x: next((f'<{c}' for c in cuts if x < c), f'>={cuts[-1]}')
    order = [f'<{c}' for c in cuts] + [f'>={cuts[-1]}']
    tab('B1 / health: the most the enemies in reach could deal this round', lambda r: b(r[0]), order)
    tab('B2 / health: the same after each has walked a step (next round)', lambda r: b(r[1]), order)
    tab('Enemies that reach this round', lambda r: min(r[2], 4), [0, 1, 2, 3, 4])
    tab('Enemies that reach next round', lambda r: min(r[3], 4), [0, 1, 2, 3, 4])
    tab('A stun reaches this round', lambda r: r[6], [False, True])
    tab('B1 share x allies within 6', lambda r: (b(r[0]), min(r[7], 2)), [(o, a) for o in order for a in (0, 1, 2)])
    # For the deaths: when was each share first crossed, counting back from the death (the run of rounds up to it).
    print('\nRounds before a death that the burst share had first been at or above (within the 8 before):')
    # rebuild runs: rows are in game order per game; a death row has r[4] == 0 and earlier rows r[4] == k.
    for name, col in (('B1', 0), ('B2', 1)):
        for thr in (0.5, 0.75, 1.0):
            first = collections.Counter()
            cur = {}
            for r in rows:
                k = r[4]
                if k > 8: continue
                if r[col] >= thr: cur.setdefault('k', k)
                if k == 0:
                    first[cur.get('k', -1)] += 1; cur = {}
            tot = sum(first.values())
            print(f'  {name} >= {thr}: never {100 * first[-1] / tot:.0f}%, only the last round {100 * first[0] / tot:.0f}%, 1 before {100 * first[1] / tot:.0f}%, 2 {100 * first[2] / tot:.0f}%, 3+ {100 * sum(v for q, v in first.items() if q >= 3) / tot:.0f}%')


if __name__ == '__main__':
    main()
