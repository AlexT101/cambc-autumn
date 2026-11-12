"""Every time enemy champions hurt our Prism: how the episode began and how it ended.

    python3 onset.py EXTROOT/TAG [--dump N] [--died]

An episode is a run of rounds in which enemy champions damage or stun the Prism, with gaps of at most GAP rounds. It
ends in death (within GAP rounds of its last hit), on our spawn, or with the Prism walking free. Read at its first
hit: the Prism's health, bag and cooldowns, who it saw at its last turn start, who was near, what it had been doing
(its last three turns), how far the hitter came from, and whether the Prism had seen it. Printed: the death rate by
each of those, so the situations that kill stand out from the ones it survives.
"""
import collections, gzip, json, os, sys
from multiprocessing import Pool

GAP = 3
MELEE = {'Ryth', 'Vendetta', 'Marcella', 'Ren', 'Varg', 'Heart of Ruin', 'Issac'}
DASH = {'Vesper Vale', 'Vendetta', 'Ren', 'Heart of Ruin', 'Issac'}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


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
    bdir = os.path.basename(os.path.dirname(meta['source']))
    opp = 'Flp4' if 'Flp4' in bdir else 'Mt3q'
    win = meta['result']['winner'] == us
    team = {c['id']: c['team'] for c in meta['champions']}
    typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}
    rounds = R['round']; idx = {r: i for i, r in enumerate(rounds)}
    prisms = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    if not prisms: return dict(prism=False, win=win, opp=opp, eps=[])
    p = prisms[0]; P = ch[p]
    spawn = mp['spawn'][us]
    foes = [c for c in ch if team[c] != us]; mates = [c for c in ch if team[c] == us and c != p]

    def pos(c, i):
        C = ch[c]
        return (C['x'][i], C['y'][i]) if i is not None and C['alive'][i] and C['x'][i] is not None else None

    # Per round: the Prism's own acts, hits on it, its death.
    acts = collections.defaultdict(list); hits = collections.defaultdict(list); death = {}
    for x in ev:
        k = x['k']; r = x['r']
        if x.get('a') == p:
            if k == 'move': acts[r].append(('M', tuple(x['f']), tuple(x['to'])))
            elif k == 'attack': acts[r].append(('Ac' if 'tgt' in x else 'Ak' if 'camp' in x else 'Al',))
            elif k == 'cast': acts[r].append((f"C{x.get('slot')}" + ('c' if x.get('dmg') else 'k' if x.get('cdmg') else '0'),))
        if k in ('attack', 'cast') and team.get(x.get('a')) == 1 - us:
            amt = sum(a for v, a in (x.get('dmg') or []) if v == p)
            st = p in (x.get('stun') or [])
            if amt > 0 or st: hits[r].append(dict(by=x['a'], amt=amt, stun=st, kind=k, f=tuple(x['f']) if x.get('f') else None, t=x['t'], s=x['s']))
        if k == 'death' and x['v'] == p: death[r] = x
    hr = sorted(hits)
    eps = []
    i = 0
    while i < len(hr):
        j = i
        while j + 1 < len(hr) and hr[j + 1] - hr[j] <= GAP and not any(q in death for q in range(hr[i], hr[j] + 1)): j += 1
        r0, r1 = hr[i], hr[j]
        died = next((q for q in range(r0, r1 + GAP + 1) if q in death), None)
        st = idx.get(r0 - 1)  # state at the start of r0
        if st is None or not P['alive'][st]:
            i = j + 1; continue
        me = pos(p, st)
        h0 = min(hits[r0], key=lambda h: h['s'])
        # Whether the Prism had acted in r0 before the first hit: its turn index against the hitter's.
        prism_first = any(True for x in ev if x['r'] == r0 and x.get('a') == p and x['s'] < h0['s'] and x['k'] in ('move', 'attack', 'cast'))
        # The state the Prism last decided on: the start of its own last turn before the hit.
        si = idx.get(r0) if prism_first else st
        sees = set(P['sees'][idx[r0]] if prism_first else (P['sees'][st] if st is not None else []))
        fo = [(c, pos(c, st)) for c in foes]; fo = [(c, q) for c, q in fo if q]
        ne6 = sum(1 for c, q in fo if cheb(me, q) <= 6); ne8 = sum(1 for c, q in fo if cheb(me, q) <= 8)
        na6 = sum(1 for c in mates if pos(c, st) and cheb(me, pos(c, st)) <= 6)
        na3 = sum(1 for c in mates if pos(c, st) and cheb(me, pos(c, st)) <= 3)
        hp = P['hp'][st] / max(1, P['maxHp'][st])
        hitter = h0['by']; hq = pos(hitter, st)
        # The Prism's last three turns before the hit.
        last = []
        for q in range(r0 - 3, r0 + (1 if prism_first else 0)):
            qi = idx.get(q)
            if qi is None: continue
            t = P['turn'][qi]
            a = acts.get(q, [])
            lab = 'stun' if t == 5 else 'oof' if t == 6 else 'chan' if t == 3 else 'dead' if t in (0, 4) else \
                  'cast@champ' if any(x[0].startswith('C') and x[0].endswith('c') for x in a) else \
                  'cast@camp' if any(x[0].startswith('C') and x[0].endswith('k') for x in a) else \
                  'hit@champ' if any(x[0] == 'Ac' for x in a) else 'hit@camp' if any(x[0] == 'Ak' for x in a) else \
                  'walk' if any(x[0] == 'M' for x in a) else 'idle'
            if lab == 'walk':
                m = next(x for x in a if x[0] == 'M')
                qs = idx.get(q - 1)
                fs = [pos(c, qs) for c in foes]; fs = [f for f in fs if f]
                if fs:
                    f0 = min(fs, key=lambda f: cheb(f, m[1]))
                    d0, d1 = cheb(f0, m[1]), cheb(f0, m[2])
                    lab = 'walk+' if d1 < d0 else 'walk-' if d1 > d0 else 'walk='
                    if d0 > 8: lab = 'walk'
            if lab == 'chan': lab = 'tribute' if P['chan'][qi] == 2 or (idx.get(q - 1) is not None and P['chan'][idx[q - 1]] == 2) else 'recall'
            last.append(lab)
        dmg = sum(h['amt'] for q in range(r0, r1 + 1) for h in hits.get(q, []))
        hitters = {h['by'] for q in range(r0, r1 + 1) for h in hits.get(q, [])}
        end = idx.get(min(r1 + GAP, rounds[-1]))
        eps.append(dict(r0=r0, r1=r1, died=died is not None, dr=died, hp=hp, gems=P['gems'][st], cd=(P['cd0'][st], P['cd1'][st]),
                        ne6=ne6, ne8=ne8, na6=na6, na3=na3, sees=len(sees), seen_hitter=hitter in sees, hitter=typ[hitter], hd=cheb(me, hq) if hq else -1,
                        first_dmg=sum(h['amt'] for h in hits[r0]), first_stun=any(h['stun'] for h in hits[r0]), prism_first=prism_first, last=last,
                        dmg=dmg, nhit=len(hitters), maxhp=P['maxHp'][st], home=max(spawn['minX'] - me[0], 0, me[0] - spawn['maxX'], spawn['minY'] - me[1], me[1] - spawn['maxY']),
                        dir=os.path.basename(d), src=meta['source'], me=me, chan=P['chan'][st],
                        seen_by=len(P['seenBy'][st]) if st is not None else 0))
        i = j + 1
    return dict(prism=True, win=win, opp=opp, eps=eps, rounds=sum(1 for a in P['alive'] if a))


def load(root):
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool:
        return [r for r in pool.map(one, dirs, chunksize=8) if r]


def table(name, E, key, order=None):
    g = collections.defaultdict(list)
    for e in E: g[key(e)].append(e)
    print(f'\n{name}')
    tot_d = sum(e['died'] for e in E)
    for k in (order or sorted(g, key=lambda k: -len(g[k]))):
        if k not in g: continue
        s = g[k]; d = sum(e['died'] for e in s)
        print(f'  {str(k):28s} {len(s):6d} episodes ({100 * len(s) / len(E):5.1f}%)  die {100 * d / len(s):5.1f}%  = {d:4d} deaths ({100 * d / max(1, tot_d):4.1f}% of them)')


def main():
    root = sys.argv[1]
    dump = int(sys.argv[sys.argv.index('--dump') + 1]) if '--dump' in sys.argv else 0
    G = [g for g in load(root) if g['prism']]
    E = [e for g in G for e in g['eps']]
    D = [e for e in E if e['died']]
    print(f'{root}: {len(G)} Prism games, {len(E)} episodes ({len(E) / len(G):.2f} a game), {len(D)} end in death ({100 * len(D) / len(E):.1f}%)')
    b = lambda x, cuts: next((f'<{c}' for c in cuts if x < c), f'>={cuts[-1]}')
    table('Health at the first hit', E, lambda e: b(e['hp'], [0.3, 0.5, 0.7, 0.9]), ['<0.3', '<0.5', '<0.7', '<0.9', '>=0.9'])
    table('Bag at the first hit', E, lambda e: b(e['gems'], [1, 20, 50, 100, 200, 400]), ['<1', '<20', '<50', '<100', '<200', '<400', '>=400'])
    table('Enemies within 6', E, lambda e: min(e['ne6'], 4), [0, 1, 2, 3, 4])
    table('Allies within 6', E, lambda e: min(e['na6'], 3), [0, 1, 2, 3])
    table('Enemies within 6 minus allies within 6 (Prism not counted)', E, lambda e: max(-2, min(3, e['ne6'] - e['na6'])), [-2, -1, 0, 1, 2, 3])
    table('Enemies the Prism saw at its last turn start', E, lambda e: min(e['sees'], 4), [0, 1, 2, 3, 4])
    table('Had it seen the first hitter', E, lambda e: e['seen_hitter'])
    table('First hitter', E, lambda e: e['hitter'])
    table('First hitter came from distance (at the round start)', E, lambda e: min(e['hd'], 7), [-1, 1, 2, 3, 4, 5, 6, 7])
    table('The Prism acted first that round', E, lambda e: e['prism_first'])
    table('Its turn before the hit', E, lambda e: e['last'][-1] if e['last'] else '?')
    table('Its last three turns: any cast or hit at a champion', E, lambda e: any(x in ('cast@champ', 'hit@champ') for x in e['last']))
    table('Spells ready at the first hit (stun, area)', E, lambda e: (e['cd'][0] <= 1, e['cd'][1] <= 1))
    table('First round: share of health taken', E, lambda e: b(e['first_dmg'] / max(1, e['hp'] * e['maxhp']), [0.15, 0.3, 0.5, 1.0]), ['<0.15', '<0.3', '<0.5', '<1.0', '>=1.0'])
    table('Stunned in the first round', E, lambda e: e['first_stun'])
    table('Distinct hitters over the episode', E, lambda e: min(e['nhit'], 4), [1, 2, 3, 4])
    table('Steps from our spawn', E, lambda e: b(e['home'], [5, 10, 20, 30]), ['<5', '<10', '<20', '<30', '>=30'])
    table('Round', E, lambda e: b(e['r0'], [150, 300, 600, 1000]), ['<150', '<300', '<600', '<1000', '>=1000'])
    table('Channel at the first hit (0 none, 1 recall, 2 tribute, 3 teleport)', E, lambda e: e['chan'])
    # Death episodes: length and the health path
    ln = sorted(e['dr'] - e['r0'] for e in D)
    print(f'\nDeath episodes: rounds from the first hit to death: median {ln[len(ln) // 2]}, quartiles {ln[len(ln) // 4]}-{ln[3 * len(ln) // 4]}; '
          f'dead in the first round {sum(1 for x in ln if x == 0)}, by the second {sum(1 for x in ln if x <= 1)}')
    if dump:
        import random
        random.seed(2)
        S = D if '--died' in sys.argv else E
        for e in random.sample(S, min(dump, len(S))):
            print({k: e[k] for k in ('dir', 'r0', 'r1', 'died', 'dr', 'hp', 'gems', 'cd', 'ne6', 'na6', 'sees', 'seen_hitter', 'hitter', 'hd', 'last', 'prism_first', 'nhit', 'home')})


if __name__ == '__main__':
    main()
