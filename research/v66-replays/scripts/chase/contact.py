# Per pursuer-round in chases: distance to the target at the previous round's end, and whether the pursuer hit it this round.
import sys, json
sys.path.insert(0, 'research/v66-replays/scripts/extract')
from common import *
from concurrent.futures import ProcessPoolExecutor
MELEE = {'Ryth','Vendetta','Marcella','Ren','Varg','Heart of Ruin','Issac'}
EP = json.load(open(sys.argv[1])); by = defaultdict(list)
for x in EP: by[x['src']].append(x)
def one(g):
    d = g['dir']; m = meta(d); R = rounds(d); rix = {r: i for i, r in enumerate(R['round'])}
    NM = {c['id']: c['name'] for c in m['champions']}; CH = R['champions']
    hit = defaultdict(float); act = defaultdict(set)
    for e in events(d):
        if 'a' in e and e['r'] in rix:
            act[(rix[e['r']], e['a'])].add(e['k'])
            if e['k'] in ('attack', 'cast'):
                for v, x in (e.get('dmg') or []): hit[(rix[e['r']], e['a'], v)] += x
    out = []
    for x in by.get(g['source'], []):
        P = [c for c in CH if NM[c['id']] == x['P'] and (c['team'] == g['us']) == (x['side'] == 'us')]
        T = [c for c in CH if NM[c['id']] == x['T'] and (c['team'] == g['us']) != (x['side'] == 'us')]
        if len(P) != 1 or len(T) != 1: continue
        P, T = P[0], T[0]; i0 = rix[x['r']]
        for j in range(i0 + 1, i0 + x['len'] + 1):
            if not (P['alive'][j] and T['alive'][j - 1]): break
            dd = cheb((P['x'][j-1], P['y'][j-1]), (T['x'][j-1], T['y'][j-1]))
            out.append((x['side'], x['P'] in MELEE, x['T'] in MELEE, dd, hit[(j, P['id'], T['id'])] > 0, 'move' in act[(j, P['id'])], x['Php'] >= .6 and x['Thp'] < .75))
    return out
if __name__ == '__main__':
    G = [g for g in games() if g['source'] in by]
    with ProcessPoolExecutor(60) as ex: res = [y for o in ex.map(one, G) for y in o]
    for pm in (True, False):
        print('pursuer', 'melee' if pm else 'ranged')
        for dd in (1, 2, 3, 4, 5):
            row = []
            for side in ('us', 'them'):
                Y = [r for r in res if r[0] == side and r[1] == pm and r[3] == dd]
                row.append('%s n=%5d hit %.2f moved %.2f' % (side, len(Y), sum(r[4] for r in Y) / max(1, len(Y)), sum(r[5] for r in Y) / max(1, len(Y))))
            print('  d=%d  ' % dd + '   |   '.join(row))
