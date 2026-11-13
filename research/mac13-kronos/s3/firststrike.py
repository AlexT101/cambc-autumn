#!/usr/bin/env python3
"""s3: Prism duels. For each Prism death by the enemy Prism and each ratio>=1.5 encounter: who stepped into cast
reach (4) first, who landed the first hit between the two, and whether the first stun decided it.
Writes replays/.s3cache/firststrike.pkl."""
import collections, os, pickle, sys
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import Game, cheb, files, load, CACHE

REACH = 4


def duel(G, a, b, i0, i1, hits):
    """Over rounds i0..i1 (indices): who entered reach first (by its own step) and who hit first."""
    entry = None
    for j in range(max(1, i0), i1 + 1):
        if not all(G.alive(c, j) and G.alive(c, j - 1) for c in (a, b)):
            continue
        d0, d1 = G.dist(a, b, j - 1), G.dist(a, b, j)
        if d0 > REACH >= d1:
            ax, ay = G.pos(a, j); ax0, ay0 = G.pos(a, j - 1)
            bx, by = G.pos(b, j); bx0, by0 = G.pos(b, j - 1)
            sa = cheb(ax, ay, bx0, by0) - cheb(ax0, ay0, bx0, by0)
            sb = cheb(bx, by, ax0, ay0) - cheb(bx0, by0, ax0, ay0)
            entry = (j + 1, 'a' if sa < 0 and sb >= 0 else 'b' if sb < 0 and sa >= 0 else 'both' if sa < 0 and sb < 0 else 'none')
            break
    first = None
    for r, s_, actor, tgt, kind, slot, stun in hits:
        if i0 + 1 <= r <= i1 + 1 and {actor, tgt} == {a, b}:
            first = (r, s_, 'a' if actor == a else 'b', kind, slot, stun)
            break
    return entry, first


def one(f):
    G = Game(load(f))
    hits = []
    for e in G.g['ev']:
        if e['k'] in ('attack', 'cast'):
            for tgt, amt in e.get('dmg', ()):
                hits.append((e['r'], e['s'], e['a'], tgt, e['k'], e.get('slot', -1), tgt in e.get('stun', ())))
    hits.sort(key=lambda h: h[1])
    out = []
    for e in G.g['ev']:
        if e['k'] != 'death' or G.names.get(e['v']) != 'Prism' or G.names.get(e.get('by')) != 'Prism':
            continue
        v, k = e['v'], e['by']
        id_ = e['r'] - 1
        i0 = id_
        while i0 > 0 and id_ - i0 < 40 and G.alive(v, i0 - 1) and G.alive(k, i0 - 1) and G.dist(v, k, i0 - 1) <= 8:
            i0 -= 1
        entry, first = duel(G, v, k, i0, id_, hits)
        out.append(dict(sha=G.g['sha'], r=e['r'], v=v, k=k, entry=entry, first=first, i0=i0,
                        k_ratio=G.power(k, max(0, i0 - 1)) / max(1, G.power(v, max(0, i0 - 1))),
                        v_br=''.join((G.branch(v, q) or ('.',))[0] for q in range(i0, id_)),
                        k_chan=G.ch[k]['chan'][max(0, i0 - 1)], v_team_won=G.team[v] == G.winner))
    return out


if __name__ == '__main__':
    with Pool(16) as p:
        rows = [r for L in p.map(one, files(), chunksize=4) for r in L]
    pickle.dump(rows, open(os.path.join(CACHE, 'firststrike.pkl'), 'wb'))
    print(len(rows))
    c = collections.Counter()
    for r in rows:
        en = r['entry'][1] if r['entry'] else 'no entry (already in reach or none)'
        en = {'a': 'victim stepped in', 'b': 'killer stepped in'}.get(en, en)
        fs = r['first'][2] if r['first'] else None
        fs = {'a': 'victim hit first', 'b': 'killer hit first', None: 'no hit between them'}[fs]
        c[(en, fs)] += 1
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print(k, v)
