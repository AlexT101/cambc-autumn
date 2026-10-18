"""Openings, territory, pack reactions and camp tanking."""
import pickle
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

from common import games, load, chebyshev, TOP, US, SHORT, ref

OUT = __file__.replace('moves.py', 'moves.pkl')


def feat(rec):
    try:
        return _feat(rec)
    except Exception:
        import traceback
        return {'rec': rec, 'error': traceback.format_exc()}


def _feat(rec):
    g = load(rec)
    M = g.map
    T = g.team_of
    camp_group = {c['id']: c['group'] for c in M.camps}
    gside = {grp['id']: grp['side'] for grp in M.groups}
    gtypes = {grp['id']: ''.join(sorted(t[0] if t != 'Gold cluster' else '$' for t in grp['types'])) for grp in M.groups}
    out = {'rec': rec, 'names': g.names, 'types': {c['id']: c['name'] for c in g.champs}, 'team_of': dict(T)}
    # opening: groups damaged per team in r1-60, champions per group, first hit round
    op = defaultdict(lambda: defaultdict(set))
    first = {}
    for e in g.events:
        if e['r'] > 60:
            break
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            t = T[e['a']]
            for cp, amt in e['cdmg']:
                gid = camp_group.get(cp)
                op[t][gid].add(e['a'])
                first.setdefault((t, gid), e['r'])
    out['opening'] = {t: [(gid, gtypes[gid], 'own' if gside[gid] == t else 'mid' if gside[gid] == -1 else 'enemy', sorted(cs), first[(t, gid)])
                          for gid, cs in sorted(op[t].items(), key=lambda x: first[(t, x[0])])] for t in (0, 1)}
    # territory: share of alive rounds in enemy half per phase
    terr = defaultdict(Counter)
    for c in g.champs:
        ch = g.ch(c['id'])
        t = c['team']
        for i in range(len(ch['x'])):
            if not ch['alive'][i]:
                continue
            ph = 0 if i < 60 else 1 if i < 200 else 2
            h = M.half(M.own(t, (ch['x'][i], ch['y'][i])))
            terr[(t, ph)]['n'] += 1
            terr[(t, ph)][h] += 1
    out['terr'] = {k: dict(v) for k, v in terr.items()}
    # pack reaction: champion sees >=3 enemies within 8, has <=1 ally within 4 (not counting self)
    react = []
    ids = list(T)
    nr = len(g.ch(ids[0])['x'])
    for c in ids:
        ch = g.ch(c)
        last = -99
        for i in range(1, nr - 4):
            if not ch['alive'][i]:
                continue
            p = (ch['x'][i], ch['y'][i])
            sees = ch['sees'][i + 1] if i + 1 < nr else []
            if not sees:
                continue
            ens = [g.pos(e, i) for e in sees]
            ens = [q for q in ens if q and chebyshev(q, p) <= 8]
            if len(ens) < 3:
                continue
            allies = [g.pos(a, i) for a in ids if T[a] == T[c] and a != c]
            na = sum(1 for q in allies if q and chebyshev(q, p) <= 4)
            if i - last < 10:
                continue
            last = i
            d0 = min(chebyshev(q, p) for q in ens)
            # after 3 rounds
            p3 = g.pos(c, i + 3)
            if p3 is None:
                outcome = 'died' if not ch['alive'][i + 3] else 'none'
                d3 = None
            else:
                e3 = [g.pos(e, i + 3) for e in sees]
                e3 = [q for q in e3 if q]
                d3 = min(chebyshev(q, p3) for q in e3) if e3 else 99
                outcome = 'home' if M.in_spawn(T[c], p3) else 'ok'
            died10 = any(not ch['alive'][j] for j in range(i, min(nr, i + 10)))
            react.append({'i': i, 'c': c, 'na': na, 'ne': len(ens), 'd0': d0, 'd3': d3, 'hp': ch['hp'][i] / ch['maxHp'][i],
                          'gems': ch['gems'][i], 'half': M.half(M.own(T[c], p)), 'outcome': outcome, 'died10': died10,
                          'chan': ch['chan'][i + 1] if i + 1 < nr else 0})
    out['react'] = react
    # camp tanking: per camp_attack session per team, share of damage on top champion
    tank = defaultdict(lambda: defaultdict(float))
    for e in g.events:
        if e['k'] == 'camp_attack' and e.get('tgt') in T:
            key = e['g']
            tank[(T[e['tgt']], e['g'], e['r'] // 25)][e['tgt']] += e.get('dmg', 0)
    tk = []
    for (t, gid, b), d in tank.items():
        tot = sum(d.values())
        if tot < 200:
            continue
        top = max(d, key=d.get)
        tk.append((t, gtypes[gid], tot, d[top] / tot, g.name_of[top], len(d)))
    out['tank'] = tk
    return out


if __name__ == '__main__':
    recs = games()
    with Pool(14) as p:
        res = p.map(feat, recs, chunksize=4)
    errs = [r for r in res if 'error' in r]
    print(len(res), 'errors', len(errs), errs[:1])
    pickle.dump([r for r in res if 'error' not in r], open(OUT, 'wb'))
