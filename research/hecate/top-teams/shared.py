"""Shared big groups (side -1, >=150 gems) and all-altar lockdowns."""
from collections import Counter, defaultdict
from multiprocessing import Pool
from common import games, load, chebyshev, TOP, US, SHORT, ref


def feat(rec):
    g = load(rec)
    M = g.map
    T = g.team_of
    big = {grp['id']: grp for grp in M.groups if grp['side'] == -1 and grp['gems'] >= 150 and 'Monolith' not in grp['types']}
    out = {'names': g.names, 'big': [], 'lock': None, 'map': g.map_name, 'winner': g.winner, 'ref': ref(rec)}
    for e in g.events:
        if e['k'] == 'group_clear' and e['g'] in big:
            i = g.start_idx(e['r'])
            tiles = [tuple(t) for t in big[e['g']]['tiles']]
            near = [sum(1 for c in g.team_ids[t] if g.pos(c, i) and min(chebyshev(g.pos(c, i), q) for q in tiles) <= 4) for t in (0, 1)]
            out['big'].append(('clear', e['r'], T.get(e.get('by')), near))
        elif e['k'] == 'capture' and e['g'] in big:
            out['big'].append(('cap', e['r'], e['team'], sum(x[1] for x in e['shares'])))
    # all-altar lockdown: first round where one team holds a lock on every altar
    locks = g.rounds['locks']
    na = len(M.altars)
    for i, row in enumerate(locks):
        for t in (0, 1):
            if na and len({(x[1], x[2]) for x in row if x[0] == t}) >= na:
                r = g.rounds['round'][i]
                opp = 1 - t
                before = g.gems_at(opp, r)
                after = g.final_gems[opp] - before
                out['lock'] = {'team': t, 'r': r, 'na': na, 'opp_after': after, 'opp_before': before, 'own_after': g.final_gems[t] - g.gems_at(t, r), 'end': g.n_rounds}
                break
        if out['lock']:
            break
    return out


if __name__ == '__main__':
    with Pool(14) as p:
        res = p.map(feat, games(), chunksize=4)
    S = defaultdict(Counter)
    L = defaultdict(list)
    for r in res:
        if r['big']:
            for t in (0, 1):
                S[r['names'][t]]['games'] += 1
            for x in r['big']:
                if x[0] == 'cap':
                    S[r['names'][x[2]]]['caps'] += 1
                    S[r['names'][x[2]]]['gems'] += x[3]
                elif x[2] is not None:
                    S[r['names'][x[2]]]['bodies'] += x[3][x[2]]
                    S[r['names'][x[2]]]['enemy_bodies'] += x[3][1 - x[2]]
                    S[r['names'][x[2]]]['clears'] += 1
        if r['lock']:
            L[r['names'][r['lock']['team']]].append(r)
    print('| team | games with a shared big group | captures/g | gems/g from it | own bodies within 4 at clear | enemy bodies within 4 |')
    print('|---|---|---|---|---|---|')
    for n in TOP + [US]:
        s = S[n]
        if s['games']:
            C = max(1, s['clears'])
            print(f"| {SHORT[n]} | {s['games']} | {s['caps']/s['games']:.2f} | {s['gems']/s['games']:.0f} | {s['bodies']/C:.1f} | {s['enemy_bodies']/C:.1f} |")
    print()
    print('| team | games where it locked every altar | median round | opponent tributes after lockdown (mean) | won |')
    print('|---|---|---|---|---|')
    from statistics import median, mean
    for n in TOP + [US]:
        l = L[n]
        if l:
            print(f"| {SHORT[n]} | {len(l)} | {median(x['lock']['r'] for x in l)} | {mean(x['lock']['opp_after'] for x in l):.0f} | {sum(1 for x in l if x['winner']==x['lock']['team'])} |")
    for n in ('Mite', 'Univardisty of Shingtonwash'):
        for x in L[n][:3]:
            print('-', SHORT[n], x['ref'], x['map'], 'r', x['lock']['r'], 'altars', x['lock']['na'], 'opp after', x['lock']['opp_after'])
