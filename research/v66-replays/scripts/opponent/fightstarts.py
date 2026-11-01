# Fight starts: who initiates, local body counts before/after (reinforcement), outcomes. -> opp/fs/<dir>.json
# A fight start = a champion-damage (or stun) hit between teams with no other cross-team champion hit within 12 tiles
# in the previous 10 rounds. Counts = alive off-spawn bodies within 8 tiles of the hit midpoint.
import sys, os, json
from collections import defaultdict, Counter
from multiprocessing import Pool
sys.path.insert(0, 'research/v66-replays/scripts/extract')
sys.path.insert(0, 'research/v66-replays/scripts/opponent')
from common import *
from feat import bfs
OUT = S + '/opp/fs'


def one(r):
    d = r['dir']
    m = meta(d); mj = mapj(m); ev = events(d); R = rounds(d)
    us = r['us']; N = len(R['round'])
    ch = R['champions']
    team = {c['id']: c['team'] for c in ch}
    name = {c['id']: c['name'] for c in m['champions']}
    D = [bfs(mj, 0), bfs(mj, 1)]
    pk = [('CI', c['team']) if name[c['id']] in ('Cassi', 'Issac') else i for i, c in enumerate(ch)]  # Cassi & Issac count as one pick

    def P(i, ri):
        c = ch[i]
        if ri < 0 or ri >= N or not c['alive'][ri] or c['x'][ri] is None: return None
        return (c['x'][ri], c['y'][ri])
    pos = [[P(i, ri) for ri in range(N)] for i in range(len(ch))]
    hits = []
    deaths = []
    for e in ev:
        if e['k'] in ('attack', 'cast'):
            a = e['a']; t = team[a]
            vs = {x for x, amt in e.get('dmg', []) if x in team and team[x] != t} | {x for x in e.get('stun', []) if x in team and team[x] != t}
            for v in vs:
                hits.append((e['r'], a, v, tuple(e['f']), tuple(e['to'])))
        elif e['k'] == 'death':
            deaths.append(e)
    starts = []
    last = []
    for h in hits:
        rr, a, v, f, to = h
        L = ((f[0] + to[0]) // 2, (f[1] + to[1]) // 2)
        if any(rr - x[0] <= 10 and cheb(L, x[1]) <= 12 for x in last):
            last.append((rr, L)); continue
        last.append((rr, L)); last = [x for x in last if rr - x[0] <= 10]
        ri = rr - 2  # end of previous round
        if ri < 0 or rr + 15 > N: continue
        def cnt(rj, t):
            return len({pk[i] for i in range(len(ch)) if ch[i]['team'] == t and pos[i][rj] is not None and cheb(pos[i][rj], L) <= 8 and D[t].get(pos[i][rj], 99) > 0})
        def hp(rj, t):
            return sum(ch[i]['hp'][rj] for i in range(len(ch)) if ch[i]['team'] == t and pos[i][rj] is not None and cheb(pos[i][rj], L) <= 8)
        ti = team[a]
        before = [cnt(ri, 0), cnt(ri, 1)]
        mx = [max(cnt(rj, t) for rj in range(ri, ri + 6)) for t in (0, 1)]
        hpb = [hp(ri, 0), hp(ri, 1)]
        kills = [0, 0]; bags = [0, 0]
        for e in deaths:
            if rr <= e['r'] <= rr + 15 and e.get('by') is not None and cheb(tuple(e['at']), L) <= 12:
                kt = team[e['by']]
                if kt != team[e['v']]: kills[kt] += 1; bags[kt] += e.get('gemsTo', 0)
        side = 'mid'
        do, dt = D[ti].get(L, 99), D[1 - ti].get(L, 99)
        side = 'init_own_half' if do < dt else ('init_enemy_half' if dt < do else 'mid')
        starts.append(dict(r=rr, init=ti, a=name[a], v=name[v], before=before, mx=mx, hpb=hpb, kills=kills, bags=bags, side=side, L=L))
    with open(f'{OUT}/{d}.json', 'w') as f:
        json.dump(dict(dir=d, map=r['map'], opp=r['opp'], us=us, won=r['won'], source=r['source'], starts=starts), f)
    return d


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    gs = games()
    with Pool(40) as p:
        for d in p.imap_unordered(one, gs): pass
    print('done')
