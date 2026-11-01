# Misc per-game: tribute context (enemies near), lock usage vs enemy tributes, teleport destinations,
# team max-HP/Strength at checkpoints, steal mechanics, initiating-hit types. -> opp/misc/<dir>.json
import sys, os, json
from collections import defaultdict, Counter
from multiprocessing import Pool
sys.path.insert(0, 'research/v66-replays/scripts/extract')
sys.path.insert(0, 'research/v66-replays/scripts/opponent')
from common import *
from feat import bfs
OUT = S + '/opp/misc'
CK = [100, 200, 300, 500, 750, 1000]


def one(r):
    d = r['dir']
    m = meta(d); mj = mapj(m); ev = events(d); R = rounds(d)
    us = r['us']; N = len(R['round'])
    ch = R['champions']
    team = {c['id']: c['team'] for c in ch}
    ix = {c['id']: i for i, c in enumerate(ch)}
    name = {c['id']: c['name'] for c in m['champions']}
    D = [bfs(mj, 0), bfs(mj, 1)]
    groups = mj['groups']
    gtiles = {tuple(t): g['id'] for g in groups for t in g['tiles']}
    altars = [tuple(a) for a in mj['altars']]
    walls = {tuple(t) for t in mj['walls']}

    def P(i, ri):
        c = ch[i]
        if ri < 0 or ri >= N or not c['alive'][ri] or c['x'][ri] is None: return None
        return (c['x'][ri], c['y'][ri])
    out = defaultdict(Counter)
    role = lambda t: 'us' if t == us else 'them'
    def add(t, meas, key, v=1): out[role(t) + '|' + meas][key] += v
    ex = defaultdict(list)
    # team stats at checkpoints
    stats = {}
    for c in CK:
        if c <= N:
            for t in (0, 1):
                cs = [x for x in ch if x['team'] == t]
                stats[f'{role(t)}|{c}'] = dict(maxhp=sum(x['maxHp'][c - 1] for x in cs), str=sum(x['str'][c - 1] for x in cs),
                                              maxhp_top=max(x['maxHp'][c - 1] for x in cs), top=name[max(cs, key=lambda x: x['maxHp'][c - 1])['id']],
                                              gold_bank=sum(x['gold'][c - 1] for x in cs))
    # tributes: enemies within 8 of the altar at end of previous round; seen by tributer at its turn start
    trib_open = {}
    for e in ev:
        k = e['k']; rr = e['r']; ri = rr - 2
        if k == 'tribute_start':
            a = e['a']; t = team[a]; alt = tuple(e['altar'])
            en = [i for i in range(len(ch)) if ch[i]['team'] != t and P(i, ri) is not None and cheb(P(i, ri), alt) <= 8]
            seen = [i for i in en if ch[i]['id'] in (ch[ix[a]]['sees'][rr - 1] or [])]
            gb = '1-9' if e['gems'] < 10 else '10-29' if e['gems'] < 30 else '30-59' if e['gems'] < 60 else '60+'
            add(t, 'trib_near', f'{min(len(en),3)}')
            add(t, 'trib_near_seen', f'{min(len(seen),3)}')
            add(t, 'trib_gb', gb)
            add(t, 'trib_gb_gems', gb, e['gems'])
            trib_open[a] = dict(r=rr, gems=e['gems'], near=len(en), seen=len(seen))
            if len(seen) >= 1 and e['gems'] >= 30 and len(ex[role(t) + '|trib_seen']) < 4:
                ex[role(t) + '|trib_seen'].append((rr, name[a], e['gems'], len(seen)))
        elif k == 'tribute_end' and e['a'] in trib_open:
            x = trib_open.pop(e['a']); add(team[e['a']], 'trib_done_near', f"{min(x['seen'],2)}|done")
        elif k == 'tribute_cancel' and e['a'] in trib_open:
            x = trib_open.pop(e['a']); add(team[e['a']], 'trib_done_near', f"{min(x['seen'],2)}|{e['cause']}")
            if e['cause'] == 'lock':
                ex[role(team[e['a']]) + '|lock_cancelled'].append((rr, name[e['a']], e['gems']))
        elif k == 'lock_place':
            t = team[e['a']]
            # was an enemy tribute running at that altar (within 1) at the time?
            hit = [a for a, x in trib_open.items() if team[a] != t]
            add(t, 'lock', 'n')
            add(t, 'lock', 'cancels_enemy_trib', int(bool(hit)))
            # own champion with gems near / about to tribute?
        elif k == 'teleport_start':
            a = e['a']; t = team[a]; to = tuple(e['to'])
            f = P(ix[a], ri)
            kind = []
            if to in gtiles: kind.append('camp_tile')
            if min((cheb(to, al) for al in altars), default=99) <= 1: kind.append('altar')
            if f is not None:
                wd = D[t].get(f, 99) - D[t].get(to, 99)
                # walk distance between f and to (approx via |D_t diff| lower bound); crossing a wall if Chebyshev small but bfs from f long
                en = [i for i in range(len(ch)) if ch[i]['team'] != t and P(i, ri) is not None and cheb(P(i, ri), f) <= 8]
                if en: kind.append('enemy_near')
                if D[1 - t].get(to, 99) < D[1 - t].get(f, 99): kind.append('toward_enemy_spawn')
            add(t, 'tele', 'n')
            for kk in kind: add(t, 'tele', kk)
            if len(ex[role(t) + '|tele']) < 4: ex[role(t) + '|tele'].append((rr, name[a], f, to, kind))
    res = dict(dir=d, map=r['map'], opp=r['opp'], us=us, won=r['won'], source=r['source'], out={k: dict(v) for k, v in out.items()}, ex=ex, stats=stats)
    with open(f'{OUT}/{d}.json', 'w') as f: json.dump(res, f)
    return d


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    with Pool(40) as p:
        for d in p.imap_unordered(one, games()): pass
    print('done')
