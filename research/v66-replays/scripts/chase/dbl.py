# In chase episodes: does the pursuer act right before or after the target, and how often does it get two turns in a row?
import sys, json, re
sys.path.insert(0, 'research/v66-replays/scripts/extract'); sys.path.insert(0, sys.argv[2])
from common import *
from order import order
from concurrent.futures import ProcessPoolExecutor
EP = json.load(open(sys.argv[1]))
by = defaultdict(list)
for x in EP: by[x['src']].append(x)
def one(g):
    d = g['dir']; m = meta(d); R = rounds(d); rix = {r: i for i, r in enumerate(R['round'])}
    NM = {c['id']: c['name'] for c in m['champions']}
    seen = defaultdict(dict)
    for e in events(d):
        if 'a' in e and 't' in e and e['r'] in rix: seen[rix[e['r']]][e['a']] = e['t']
    def before(i, a, b):  # a acts before b in round index i
        s = seen.get(i, {})
        if a in s and b in s: return s[a] < s[b]
        seq = order(R, i, 1); return seq.index(a) < seq.index(b)
    ids = {v: k for k, v in NM.items()}
    out = []
    for x in by.get(g['source'], []):
        # find ids: names are unique per team except mirror picks; pick by team side
        P = [c for c in R['champions'] if NM[c['id']] == x['P'] and (c['team'] == g['us']) == (x['side'] == 'us')]
        T = [c for c in R['champions'] if NM[c['id']] == x['T'] and (c['team'] == g['us']) != (x['side'] == 'us')]
        if len(P) != 1 or len(T) != 1: continue
        p, t = P[0]['id'], T[0]['id']; i0 = rix[x['r']]
        rows = [before(i, p, t) for i in range(i0 + 1, i0 + x['len'] + 1)]
        if len(rows) < 2: continue
        # P double: after T in round j-1, before T in round j
        pd = sum(1 for a, b in zip(rows, rows[1:]) if not a and b); td = sum(1 for a, b in zip(rows, rows[1:]) if a and not b)
        out.append(dict(side=x['side'], end=x['end'], first=sum(rows) / len(rows), pd=pd, td=td, n=len(rows) - 1, Tdied20=x['Tdied20'], Php=x['Php'], Thp=x['Thp']))
    return out
if __name__ == '__main__':
    G = [g for g in games() if g['source'] in by]
    with ProcessPoolExecutor(60) as ex: res = [y for o in ex.map(one, G) for y in o]
    for lab, f in (('all', lambda x: True), ('P healthy, T<.75', lambda x: x['Php'] >= .6 and x['Thp'] < .75)):
        print('==', lab)
        for side in ('us', 'them'):
            Y = [x for x in res if x['side'] == side and f(x)]
            n = sum(x['n'] for x in Y)
            print('  pursuer %-4s eps %5d  P acts first %.2f  P doubles/boundary %.3f  T doubles/boundary %.3f' % (side, len(Y), sum(x['first'] for x in Y) / len(Y), sum(x['pd'] for x in Y) / n, sum(x['td'] for x in Y) / n))
            for k, ff in (('P first >=.75', lambda v: v >= .75), ('mixed', lambda v: .25 < v < .75), ('P first <=.25', lambda v: v <= .25)):
                Z = [x for x in Y if ff(x['first'])]
                if Z: print('     %-14s n=%5d  T dies<=20r %.2f  kill-end %.2f' % (k, len(Z), sum(x['Tdied20'] for x in Z) / len(Z), sum(x['end'] == 'kill' for x in Z) / len(Z)))
    json.dump(res, open(sys.argv[1].replace('.json', '-order.json'), 'w'))
    print('== by target hp, pursuer healthy')
    for lo, hi in ((0, .35), (.35, .6), (.6, .85), (.85, 1.01)):
        for side in ('us', 'them'):
            Y = [x for x in res if x['side'] == side and x['Php'] >= .6 and lo <= x['Thp'] < hi]
            a = [x for x in Y if x['first'] <= .25]; b = [x for x in Y if x['first'] >= .75]
            f = lambda Z: '%.2f (n=%d)' % (sum(x['Tdied20'] for x in Z) / max(1, len(Z)), len(Z))
            print('  T %.2f-%.2f %-4s  P after T: %s   P before T: %s' % (lo, hi, side, f(a), f(b)))
