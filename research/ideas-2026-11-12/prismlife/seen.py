"""Who saw the enemies that killed our Prism: python3 seen.py EXTROOT/TAG
For each Prism death to champions: the enemies that damaged or stunned it in the 8 rounds before (its hitters). At K
rounds before the death (K = 2, 4, 6, 8), for each hitter alive then: seen by the Prism at its turn start that round,
else by a teammate at theirs, else by nobody. Also the same for every enemy within 12 of the Prism then (the pack)."""
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
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {q: i for i, q in enumerate(rounds)}
    pr = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; P = ch[p]; mates = [c for c in ch if team[c] == us and c != p]; foes = [c for c in ch if team[c] != us]
    hits = collections.defaultdict(set)
    for x in ev:
        if x['k'] in ('attack', 'cast') and team.get(x.get('a')) == 1 - us:
            if any(v == p for v, _ in (x.get('dmg') or [])) or p in (x.get('stun') or []): hits[x['r']].add(x['a'])
    out = []
    for x in ev:
        if x['k'] != 'death' or x['v'] != p or x.get('by') is None: continue
        r = x['r']; H = set()
        for q in range(r - 8, r + 1): H |= hits.get(q, set())
        row = dict(n=len(H), k={})
        for K in (2, 4, 6, 8):
            i = idx.get(r - K)
            if i is None or not P['alive'][i] or P['x'][i] is None: continue
            me = (P['x'][i], P['y'][i])
            ps = set(P['sees'][i]); ms = set()
            for m in mates:
                if ch[m]['alive'][i]: ms |= set(ch[m]['sees'][i])
            c = collections.Counter(); far = collections.Counter()
            for h in H:
                if not ch[h]['alive'][i] or ch[h]['x'][i] is None: continue
                dd = cheb(me, (ch[h]['x'][i], ch[h]['y'][i]))
                c['prism' if h in ps else 'ally' if h in ms else 'nobody'] += 1
                if h not in ps: far['<=8' if dd <= 8 else '<=12' if dd <= 12 else '>12'] += 1
            pk = collections.Counter()
            for e in foes:
                if not ch[e]['alive'][i] or ch[e]['x'][i] is None or cheb(me, (ch[e]['x'][i], ch[e]['y'][i])) > 12: continue
                pk['prism' if e in ps else 'ally' if e in ms else 'nobody'] += 1
            row['k'][K] = (dict(c), dict(far), dict(pk))
        out.append(row)
    return out


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    print(len(R), 'Prism deaths to champions; hitters a death', sum(r['n'] for r in R) / len(R))
    for K in (2, 4, 6, 8):
        c = collections.Counter(); far = collections.Counter(); pk = collections.Counter(); n = 0; any_unseen = 0; any_ally = 0
        for r in R:
            if K not in r['k']: continue
            a, f, k2 = r['k'][K]; n += 1
            c.update(a); far.update(f); pk.update(k2)
            any_unseen += (a.get('ally', 0) + a.get('nobody', 0)) > 0; any_ally += a.get('ally', 0) > 0
        t = sum(c.values()); tp = sum(pk.values())
        print(f'{K} rounds before ({n} deaths): its hitters seen by the Prism {100 * c["prism"] / t:.0f}%, by a teammate only {100 * c["ally"] / t:.0f}%, by nobody {100 * c["nobody"] / t:.0f}%;'
              f' deaths with a hitter it did not see {100 * any_unseen / n:.0f}%, with one a teammate saw {100 * any_ally / n:.0f}%;'
              f' unseen hitters by distance: ' + ', '.join(f'{a} {100 * b / max(1, sum(far.values())):.0f}%' for a, b in sorted(far.items()))
              + f'; enemies within 12: Prism {100 * pk["prism"] / tp:.0f}%, teammate only {100 * pk["ally"] / tp:.0f}%, nobody {100 * pk["nobody"] / tp:.0f}%')
