"""Body-advantage windows (r>=100): a team with 2+ more alive bodies. How long they last, where its bodies stand, what
it captures on the enemy half in them vs at parity, and the gems sitting on the enemy half's ready/cleared groups."""
import gzip, json, sys, collections, os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
def g(d):
    meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    mp = json.load(open(os.path.join(d, meta['mapFile'])))
    sp = [((s['minX']+s['maxX'])/2, (s['minY']+s['maxY'])/2) for s in mp['spawn']]
    side = {}
    for G in mp['groups']:
        cx = sum(t[0] for t in G['tiles'])/len(G['tiles']); cy = sum(t[1] for t in G['tiles'])/len(G['tiles'])
        d0, d1 = cheb((cx, cy), sp[0]), cheb((cx, cy), sp[1]); s = d0/max(1, d0+d1)
        side[G['id']] = 0 if s < 0.4 else 1 if s > 0.6 else 'mid'
    gems = {G['id']: G['gems'] for G in mp['groups']}
    ch = R['champions']; n = len(R['round'])
    adv = []
    for i in range(n):
        al = [sum(1 for c in ch if int(c['team']) == t and c['alive'][i]) for t in (0, 1)]
        adv.append(al[0]-al[1])
    out = collections.Counter()
    # window lengths
    for t in (0, 1):
        sgn = 1 if t == 0 else -1
        run = 0
        for i in range(100, n):
            if sgn*adv[i] >= 2: run += 1
            elif run: out['win_n'] += 1; out['win_len'] += run; run = 0
        if run: out['win_n'] += 1; out['win_len'] += run
    caps = []
    for l in gzip.open(d/'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'capture' and e['r'] >= 100:
            caps.append((e['r'], e['team'], e['g']))
    for r, t, gid in caps:
        a = adv[min(r, n-1)] * (1 if t == 0 else -1)
        st = 'ahead2' if a >= 2 else 'ahead1' if a == 1 else 'par' if a == 0 else 'behind'
        sd = side[gid]
        where = 'own' if sd == t else 'mid' if sd == 'mid' else 'enemy'
        out[('cap', st, where)] += gems[gid]
    for i in range(100, n):
        for t in (0, 1):
            a = adv[i]*(1 if t == 0 else -1)
            st = 'ahead2' if a >= 2 else 'ahead1' if a == 1 else 'par' if a == 0 else 'behind'
            out[('rounds', st)] += 1
    return out
if __name__ == '__main__':
    dirs = [d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    T = collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(g, dirs, chunksize=8): T.update(r)
    print('2+ ahead windows per team-game', round(T['win_n']/len(dirs)/2, 2), 'mean length', round(T['win_len']/max(1, T['win_n']), 1))
    for st in ('ahead2', 'ahead1', 'par', 'behind'):
        r = T[('rounds', st)]
        print(st, 'team-rounds share', round(r/sum(T[('rounds', s)] for s in ('ahead2', 'ahead1', 'par', 'behind')), 3),
              'capture gems per 100 team-rounds own/mid/enemy', *[round(100*T[('cap', st, w)]/max(1, r), 2) for w in ('own', 'mid', 'enemy')])
