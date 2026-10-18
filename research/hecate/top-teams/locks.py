"""Altar lock usage: when placed, what it cancels, lifetime."""
from collections import Counter, defaultdict
from multiprocessing import Pool
from common import games, load, chebyshev, TOP, US, SHORT, ref


def feat(rec):
    g = load(rec)
    M = g.map
    T = g.team_of
    out = []
    ev = g.events
    for j, e in enumerate(ev):
        if e['k'] != 'lock_place':
            continue
        t = T[e['a']]
        to = tuple(e['to'])
        canc = [x for x in ev[j:j + 30] if x['s'] == e['s'] and x['k'] == 'tribute_cancel' and x.get('cause') == 'lock']
        en = [x for x in canc if T[x['a']] != t]
        own = [x for x in canc if T[x['a']] == t]
        dest = next((x['r'] for x in ev[j:] if x['k'] == 'lock_destroyed' and x.get('team') == t and tuple(x.get('at') or ()) == to), None)
        h = M.half(M.own(t, to))
        nalt = len(M.altars)
        # enemy tributes at this altar afterwards while locked
        out.append({'r': e['r'], 'team': t, 'enemy_cancel': len(en), 'gems_denied': sum(x['gems'] for x in en), 'own_cancel': len(own),
                    'life': (dest or g.n_rounds) - e['r'], 'destroyed': dest is not None, 'half': h, 'nalt': nalt,
                    'ref': ref(rec, e['r'])})
    return {'rec': rec, 'names': g.names, 'locks': out}


if __name__ == '__main__':
    with Pool(14) as p:
        res = p.map(feat, games(), chunksize=4)
    st = defaultdict(Counter)
    ex = defaultdict(list)
    for r in res:
        for t in (0, 1):
            st[r['names'][t]]['games'] += 1
        for l in r['locks']:
            n = r['names'][l['team']]
            s = st[n]
            s['n'] += 1
            s['ec'] += l['enemy_cancel'] > 0
            s['gd'] += l['gems_denied']
            s['oc'] += l['own_cancel'] > 0
            s['life'] += l['life']
            s['destroyed'] += l['destroyed']
            s['h' + str(l['half'])] += 1
            s['early'] += l['r'] <= 150
            if l['enemy_cancel'] and len(ex[n]) < 4:
                ex[n].append(l['ref'] + f" denied {l['gems_denied']}")
    print('| team | locks/g | cancelled an enemy tribute | gems in cancelled channels | placed in own/mid/enemy half | placed by r150 | destroyed | mean life (rounds) |')
    print('|---|---|---|---|---|---|---|---|')
    for n in TOP + [US]:
        s = st[n]
        N = max(1, s['n'])
        print(f"| {SHORT[n]} | {s['n']/s['games']:.2f} | {100*s['ec']/N:.0f}% | {s['gd']} | {s['h0']}/{s['h-1']}/{s['h1']} | {100*s['early']/N:.0f}% | {100*s['destroyed']/N:.0f}% | {s['life']/N:.0f} |")
    for n in ex:
        print('-', SHORT.get(n, n), '; '.join(ex[n]))
