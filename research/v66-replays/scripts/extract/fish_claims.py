# Teammate's two observations about the opponents:
# 1) camp deaths instead of champion kills when death is certain: camp deaths with an enemy champion near (kill denied), per team.
# 2) Cassi & Issac do camp work but leave the capture rewards (gems/gold) to other champions: per type, share of the team's
#    camp damage vs share of capture gems+gold, and gold spent.
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(g):
    d = g['dir']; m = meta(d); R = rounds(d); us = g['us']
    team = {c['id']: c['team'] for c in m['champions']}; NM = {c['id']: c['name'] for c in m['champions']}
    CH = {c['id']: c for c in R['champions']}; ri = {rn: i for i, rn in enumerate(R['round'])}
    o = Counter()
    for e in events(d):
        side = lambda cid: 'us' if team[cid] == us else g['opp']
        if e['k'] == 'death' and e.get('linked') is None:
            s = side(e['v']); o[(s, 'deaths')] += 1
            if e.get('by') is None:
                i = ri.get(e['r'] - 1)
                near = i is not None and any(team[c] != team[e['v']] and CH[c]['alive'][i] and cheb((CH[c]['x'][i], CH[c]['y'][i]), tuple(e['at'])) <= 4 for c in CH)
                o[(s, 'camp_deaths')] += 1; o[(s, 'camp_deaths_enemy_near')] += near
                o[(s, 'camp_death_gems')] += e['gems']
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            o[(side(e['a']), 'campdmg', NM[e['a']])] += sum(a for _, a in e['cdmg'])
        if e['k'] == 'capture':
            for cid, gm, gd in e['shares']:
                o[(side(cid), 'capgems', NM[cid])] += gm; o[(side(cid), 'capgold', NM[cid])] += gd
    return o
if __name__ == '__main__':
    with ProcessPoolExecutor(30) as ex: res = list(ex.map(one, games()))
    T = Counter()
    for o in res: T.update(o)
    sides = ['us', 'Fish', 'Mite', 'UoS', 'PBG']
    print('1) camp deaths')
    for s in sides:
        print('  %-5s deaths %5d  camp deaths %4d (%.1f%%)  with an enemy champion within 4: %4d  gems lost to camps %d' % (
            s, T[(s, 'deaths')], T[(s, 'camp_deaths')], 100 * T[(s, 'camp_deaths')] / max(1, T[(s, 'deaths')]), T[(s, 'camp_deaths_enemy_near')], T[(s, 'camp_death_gems')]))
    print('2) share of team camp damage vs share of capture gems / gold, by type')
    for s in sides:
        cd = sum(v for k, v in T.items() if k[0] == s and k[1] == 'campdmg'); cg = sum(v for k, v in T.items() if k[0] == s and k[1] == 'capgems'); cgo = sum(v for k, v in T.items() if k[0] == s and k[1] == 'capgold')
        rows = []
        for nm in sorted({k[2] for k in T if k[0] == s and len(k) == 3}):
            rows.append('%s %.2f/%.2f/%.2f' % (nm[:7], T[(s, 'campdmg', nm)] / cd, T[(s, 'capgems', nm)] / max(1, cg), T[(s, 'capgold', nm)] / max(1, cgo)))
        print('  %-5s' % s, ' | '.join(rows))
