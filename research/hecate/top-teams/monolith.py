"""Monolith sieges: duration, damage taken, contributors, from range."""
from collections import Counter, defaultdict
from statistics import mean, median
from multiprocessing import Pool
from common import games, load, chebyshev, TOP, US, SHORT, ref


def feat(rec):
    g = load(rec)
    M = g.map
    T = g.team_of
    mono = {c['id']: c for c in M.camps if c['type'] == 'Monolith'}
    if not mono:
        return None
    mg = {c['group'] for c in mono.values()}
    life = defaultdict(lambda: {'dmg': Counter(), 'taken': Counter(), 'first': None, 'champs': defaultdict(float), 'far': Counter(), 'deaths': Counter()})
    out = []
    for e in g.events:
        k = e['k']
        if k in ('attack', 'cast') and e.get('cdmg'):
            for c, amt in e['cdmg']:
                if c in mono:
                    L = life[mono[c]['group']]
                    t = T[e['a']]
                    L['dmg'][t] += amt
                    L['champs'][e['a']] += amt
                    if chebyshev(tuple(e['f']), (mono[c]['x'], mono[c]['y'])) >= 4:
                        L['far'][t] += amt
                    L['first'] = L['first'] or e['r']
        elif k == 'camp_attack' and e.get('g') in mg and e.get('tgt') in T:
            life[e['g']]['taken'][T[e['tgt']]] += e.get('dmg', 0)
        elif k == 'death' and e.get('by') is None and 'linked' not in e:
            for gg, L in life.items():
                if L['first']:
                    p = tuple(e['at'])
                    if any(chebyshev(p, (c['x'], c['y'])) <= 3 for c in mono.values() if c['group'] == gg):
                        L['deaths'][T[e['v']]] += 1
        elif k == 'group_clear' and e['g'] in mg:
            L = life.pop(e['g'])
            t = T.get(e.get('by'))
            out.append({'team': t, 'r': e['r'], 'dur': e['r'] - (L['first'] or e['r']), 'taken': L['taken'][t], 'far': L['far'][t] / max(1, L['dmg'][t]),
                        'share': L['dmg'][t] / max(1, sum(L['dmg'].values())), 'n': sum(1 for c, v in L['champs'].items() if T[c] == t and v > 500),
                        'types': sorted(g.name_of[c] for c, v in L['champs'].items() if T[c] == t and v > 500), 'deaths': L['deaths'][t], 'ref': ref(rec, e['r'])})
    caps = [e for e in g.events if e['k'] == 'capture' and e['g'] in mg]
    return {'names': g.names, 'clears': out, 'caps': [(e['team'], e['r'], sum(x[1] for x in e['shares'])) for e in caps], 'map': g.map_name, 'N': g.n_rounds}


if __name__ == '__main__':
    with Pool(14) as p:
        res = [r for r in p.map(feat, games(), chunksize=4) if r]
    S = defaultdict(list)
    caps = defaultdict(Counter)
    for r in res:
        for t in (0, 1):
            caps[r['names'][t]]['games'] += 1
        for c in r['clears']:
            if c['team'] is None:
                continue
            S[r['names'][c['team']]].append(c)
        for t, rr, gems in r['caps']:
            caps[r['names'][t]]['caps'] += 1
            caps[r['names'][t]]['gems'] += gems
            if rr <= 300:
                caps[r['names'][t]]['early'] += 1
    print('| team | games on monolith maps | monolith captures/g | by r300 | clears | median rounds first hit to clear | median damage taken from monolith | dealt from 4+ | champions >500 dmg | camp deaths near monolith per clear |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for n in TOP + [US]:
        s = S[n]
        c = caps[n]
        if not s:
            print(f"| {SHORT[n]} | {c['games']} | {c['caps']/max(1,c['games']):.2f} | | 0 |")
            continue
        print(f"| {SHORT[n]} | {c['games']} | {c['caps']/c['games']:.2f} | {c['early']} | {len(s)} | {median(x['dur'] for x in s)} | {median(x['taken'] for x in s):.0f} | {100*mean(x['far'] for x in s):.0f}% | {mean(x['n'] for x in s):.1f} | {mean(x['deaths'] for x in s):.2f} |")
    for n in ('Mite', 'Intercontinental Fish', US):
        for x in S[n][:3]:
            print('-', SHORT[n], x['ref'], x['types'], 'dur', x['dur'], 'taken', round(x['taken']), 'far %.2f' % x['far'])
