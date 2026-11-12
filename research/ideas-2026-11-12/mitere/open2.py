"""Opening farm efficiency (first 200 rounds), both teams of each game: clear episodes, captures, body activity.
Usage: python3 open2.py OUT.jsonl.gz SRCS(live,ranked) [procs]
Per game and team: earned gold at r50/100/150/200, clear episodes (group, value, distance, first hit, clear, attackers
with first hit and damage, capture round/team/shares, hold start), and per-body activity counts by round bucket."""
import sys, json, gzip, collections
from multiprocessing import Pool
import ml
from feat import blockers, bfs
LIM = 200
def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
def one(sd):
    try:
        g = ml.load(sd)
    except Exception:
        return None
    if g is None: return None
    m, rd, ev, mp = g['meta'], g['rd'], g['ev'], g['map']
    team = {c['id']: c['team'] for c in m['champions']}; name = {c['id']: c['name'] for c in m['champions']}
    C = {c['id']: c for c in rd['champions']}; nR = len(rd['round'])
    blk = blockers(mp)
    sp = [((s['minX'] + s['maxX']) // 2, (s['minY'] + s['maxY']) // 2) for s in mp['spawn']]
    dsp = [bfs(mp, blk - {sp[t]}, sp[t]) for t in (0, 1)]
    camp2g = {c['id']: c['group'] for c in mp['camps']}
    ghp = collections.Counter()
    for c in mp['camps']: ghp[c['group']] += c['hp']
    G = {q['id']: q for q in mp['groups']}
    tiles = {q['id']: set(map(tuple, q['tiles'])) for q in mp['groups']}
    def gd(gid, t): return min([dsp[t].get(tl, 999) for tl in tiles[gid]] or [999])
    # rank of groups by walk distance from each spawn
    rank = [{gid: i for i, (d, gid) in enumerate(sorted((gd(q, t), q) for q in G))} for t in (0, 1)]
    ep = {}  # (gid, team) -> open episode
    eps = []
    hits = collections.defaultdict(set)  # (r, cid) -> 'camp'/'champ'
    holdstart = {}
    for e in ev:
        r = e['r']
        if r > LIM + 20: break
        k = e['k']
        if k in ('attack', 'cast'):
            a = e['a']
            cd = e.get('cdmg') or []
            if e.get('camp') is not None and not cd: cd = [[e['camp'], 0]]
            for cid, dm in cd:
                gid = camp2g.get(cid)
                if gid is None: continue
                hits[(r, a)].add('camp')
                key = (gid, team[a])
                if key not in ep:
                    ep[key] = {'g': gid, 't': team[a], 'hit0': r, 'att': {}, 'dmg': collections.Counter(), 'clear': None, 'by': None}
                ep[key]['att'].setdefault(a, r); ep[key]['dmg'][a] += dm
            for x in e.get('dmg', []):
                if x[0] in team and team[x[0]] != team[a]: hits[(r, a)].add('champ')
        elif k == 'group_clear':
            gid = e['g']; by = e.get('by')
            for t in (0, 1):
                key = (gid, t)
                if key in ep:
                    x = ep.pop(key); x['clear'] = r; x['by'] = team.get(by) if by is not None else None
                    x['cap'] = None; eps.append(x)
        elif k == 'capture_hold':
            holdstart.setdefault((e['g'], e['team']), []).append(r)
        elif k == 'capture':
            for x in reversed(eps):
                if x['g'] == e['g'] and x.get('cap') is None and x['clear'] <= r:
                    x['cap'] = [r, e['team'], e['shares']]
                    hs = [h for h in holdstart.get((e['g'], e['team']), []) if x['clear'] <= h <= r]
                    x['hold0'] = hs[0] if hs else None
                    break
    out_eps = []
    for x in eps:
        if x['hit0'] > LIM: continue
        q = G[x['g']]; t = x['t']
        out_eps.append({'g': x['g'], 't': t, 'types': q['types'], 'gold': q['gold'], 'gems': q['gems'], 'hp': ghp[x['g']], 'dist': gd(x['g'], t),
                        'rank': rank[t][x['g']], 'hit0': x['hit0'], 'clear': x['clear'], 'by': x['by'],
                        'att': {str(a): [r0, round(x['dmg'][a]), name[a]] for a, r0 in x['att'].items()}, 'cap': x.get('cap'), 'hold0': x.get('hold0')})
    # body activity per round: camp hit, champ hit, holding (on a capture tile of a cleared group), moved, idle, chan, dead
    capt = set()
    for q in mp['groups']:
        for tl in q['tiles']: capt.add(tuple(tl))
    act = {}
    for cid, c in C.items():
        a = collections.Counter()
        for r in range(2, min(LIM, nR) + 1):
            i0, i1 = r - 2, r - 1
            if not c['alive'][i1]: a['dead'] += 1; continue
            h = hits.get((r, cid), set())
            p1 = (c['x'][i1], c['y'][i1]); p0 = (c['x'][i0], c['y'][i0]) if c['alive'][i0] else p1
            if 'champ' in h: a['champ'] += 1
            elif 'camp' in h: a['camp'] += 1
            elif p1 in capt: a['hold'] += 1
            elif p1 != p0: a['move'] += 1
            elif c['chan'][i1] == 2: a['chan'] += 1
            else: a['idle'] += 1
        act[str(cid)] = dict(a)
    earned = {r: [sum(C[c]['earned'][min(r, nR) - 1] for c in C if team[c] == t) for t in (0, 1)] for r in (50, 100, 150, 200)}
    # clump: largest group within 5 of a body as a share of alive bodies, per team, every 5 rounds
    clump = {}
    for t in (0, 1):
        s = []
        for i in range(0, min(LIM, nR), 5):
            P = [(C[c]['x'][i], C[c]['y'][i]) for c in C if team[c] == t and C[c]['alive'][i] and name[c] != 'Issac']
            if len(P) >= 2: s.append(max(sum(1 for q in P if cheb(p, q) <= 5) for p in P) / len(P))
        clump[t] = s
    return {'mid': g['mid'], 'src': g['src'], 'ver': g['ver'], 'mite': g['mite'], 'win': g['win'], 'map': g['mapname'], 'opp': g['opp'],
            'champs': [[c['id'], c['team'], c['name']] for c in m['champions']], 'eps': out_eps, 'act': act, 'earned': earned, 'clump': clump,
            'ngroups': len(G)}

if __name__ == '__main__':
    outp = sys.argv[1]; srcs = sys.argv[2].split(','); procs = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    ds = [d for s in srcs for d in ml.dirs(s)]
    with Pool(procs) as P, gzip.open(outp, 'wt') as f:
        n = 0
        for o in P.imap_unordered(one, ds, chunksize=2):
            if o is None: continue
            f.write(json.dumps(o) + '\n'); n += 1
    print('wrote', n)
