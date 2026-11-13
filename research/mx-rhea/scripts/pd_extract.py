"""Prism hunt / Prism-death features from the mirror extraction (replays/ana-mirror), with D-line branches from the debug replays.
Writes research/mx-rhea/scripts/pd_rows.pkl: per game {episodes, death (first Prism death to a champion), onsets}.
Usage (repo root): py research/mx-rhea/scripts/pd_extract.py [N]"""
import sys, json, gzip, zipfile, pickle
from collections import deque
from pathlib import Path
from multiprocessing import Pool

ANA = Path('replays/ana-mirror')
PRISM = 6

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

def bfs_from_spawn(m, sp):
    W, H = m['width'], m['height']
    blk = set(map(tuple, m['walls'])) | set(map(tuple, m['holes'])) | set(map(tuple, m['altars']))
    INF = 10 ** 6
    d = [[INF] * H for _ in range(W)]
    q = deque()
    for x in range(sp['minX'], sp['maxX'] + 1):
        for y in range(sp['minY'], sp['maxY'] + 1):
            d[x][y] = 0; q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if (dx or dy) and 0 <= nx < W and 0 <= ny < H and d[nx][ny] == INF and (nx, ny) not in blk:
                    d[nx][ny] = d[x][y] + 1; q.append((nx, ny))
    return d

def on_spawn(p, sp): return sp['minX'] <= p[0] <= sp['maxX'] and sp['minY'] <= p[1] <= sp['maxY']

def branches(src):
    z = zipfile.ZipFile(src)
    br = {}
    for side in 'ab':
        try: s = z.read(f'team-{side}.stdout').decode(errors='replace').splitlines()
        except KeyError: continue
        for l in s:
            l = l.lstrip('\x00')
            if l.startswith('D '):
                p = l.split()
                if len(p) >= 4: br[(int(p[2]), int(p[1]))] = p[3]
    return br

def one(d):
    gd = ANA / d
    meta = json.load(open(gd / 'meta.json'))
    R = json.load(gzip.open(gd / 'rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(gd / 'events.jsonl.gz', 'rt')]
    m = json.load(open(gd / meta['mapFile']))
    spawn = m['spawn']
    cen = [((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2) for s in spawn]
    dist_sp = [bfs_from_spawn(m, spawn[0]), bfs_from_spawn(m, spawn[1])]
    ch = R['champions']
    pr = {c['team']: c for c in ch if next(mc for mc in meta['champions'] if mc['id'] == c['id'])['type'] == PRISM}
    if len(pr) != 2: return None
    winner = meta['result']['winner']
    rounds = R['round']; N = len(rounds)
    ri = {r: i for i, r in enumerate(rounds)}
    br = branches(meta['source'])
    deaths = [e for e in ev if e['k'] == 'death']
    stun_ev = {}  # victim -> rounds stunned by an action
    for e in ev:
        if e['k'] in ('cast', 'attack') and e.get('stun'):
            for v in e['stun']: stun_ev.setdefault(v, set()).add(e['r'])

    def pos(c, i): return (c['x'][i], c['y'][i]) if c['alive'][i] and c['x'][i] is not None else None

    def near(c, i, team, rad=8, excl=()):
        p = pos(c, i)
        if p is None: return []
        return [o['id'] for o in ch if o['team'] == team and o['id'] != c['id'] and o['id'] not in excl and pos(o, i) and cheb(pos(o, i), p) <= rad]

    def death_of(cid, r0, r1):
        for e in deaths:
            if e['v'] == cid and r0 <= e['r'] <= r1: return e
        return None

    out = {'dir': d, 'winner': winner, 'rounds': N, 'map': meta['map']['name'], 'prism': {t: pr[t]['id'] for t in pr}}
    # Q1 episodes
    eps = []
    for st in (0, 1):
        S, V = pr[st], pr[1 - st]; vt = 1 - st
        opp = []
        for i in range(N):
            ps, pv = pos(S, i), pos(V, i)
            if ps is None or pv is None or on_spawn(pv, spawn[vt]): continue
            if V['id'] not in (S['sees'][i] or []): continue
            dd = cheb(ps, pv)
            if not 5 <= dd <= 9: continue
            if S['foc'][i] < 1.2 * V['foc'][i] or S['hp'][i] < 0.6 * S['maxHp'][i]: continue
            opp.append(i)
        groups = []
        for i in opp:
            if groups and rounds[i] - rounds[groups[-1][-1]] <= 5: groups[-1].append(i)
            else: groups.append([i])
        for g in groups:
            i0 = g[0]; r0 = rounds[i0]
            ps, pv = pos(S, i0), pos(V, i0)
            dv = dist_sp[vt][pv[0]][pv[1]]
            allies = near(V, i0, st, 8, excl=(S['id'],))
            esc = [a for a in allies if (lambda p: dist_sp[vt][p[0]][p[1]] < dv)(pos(next(o for o in ch if o['id'] == a), i0))]
            esc_c = [a for a in allies if (lambda p: cheb(p, cen[vt]) < cheb(pv, cen[vt]))(pos(next(o for o in ch if o['id'] == a), i0))]
            vallies = near(V, i0, vt, 8)
            de = death_of(V['id'], r0, r0 + 20)
            sde = death_of(S['id'], r0, r0 + 20)
            rend = de['r'] if de else r0 + 20
            closed = False; minD = 99; reached_sp = False; regroup = False
            for j in range(i0, min(N, ri.get(rend, N - 1) + 1)):
                a, b = pos(S, j), pos(V, j)
                if a and b:
                    minD = min(minD, cheb(a, b))
                if b and on_spawn(b, spawn[vt]) and not (de and rounds[j] >= de['r']): reached_sp = True
                if b and (not de or rounds[j] < de['r']):
                    k = sum(1 for o in ch if o['team'] == vt and o['id'] != V['id'] and pos(o, j) and cheb(pos(o, j), b) <= 3)
                    if k >= 2: regroup = True
            bS = br.get((S['id'], r0), '?'); bV = br.get((V['id'], r0), '?')
            eps.append(dict(st=st, r0=r0, r1=rounds[g[-1]], n=len(g), d0=cheb(ps, pv), fS=S['foc'][i0], fV=V['foc'][i0],
                            hpV=V['hp'][i0] / V['maxHp'][i0], gemsV=V['gems'][i0], allies=len(allies), esc=len(esc), esc_c=len(esc_c),
                            vallies=len(vallies), dvsp=dv, died=bool(de), dr=(de['r'] - r0) if de else None,
                            by=(('S' if de.get('by') == S['id'] else ('ally' if de.get('by') is not None else 'camp')) if de else None),
                            Sdied=bool(sde), closed=minD <= 4, minD=minD, reached_sp=reached_sp, regroup=regroup,
                            bS=bS, bV=bV, Swin=(st == winner), seenV=S['id'] in (V['sees'][i0] or [])))
    out['episodes'] = eps
    # Q2 first Prism death to a champion
    pd = [e for e in deaths if e['v'] in (pr[0]['id'], pr[1]['id']) and e.get('by') is not None]
    out['death'] = None
    if pd:
        e = pd[0]; vt = 0 if e['v'] == pr[0]['id'] else 1
        Vc, Ec = pr[vt], pr[1 - vt]
        rd = e['r']; idd = ri.get(rd, N - 1)
        win = []
        for j in range(max(0, idd - 40), idd + 1):
            r = rounds[j]
            # state rows are end-of-round: for the death round use the previous row's positions
            jj = j if j < idd else max(0, idd - 1)
            pv, pe = pos(Vc, jj), pos(Ec, jj)
            win.append(dict(r=r, b=br.get((Vc['id'], r), '?'), be=br.get((Ec['id'], r), '?'),
                            dist=cheb(pv, pe) if pv and pe else None, ealive=bool(Ec['alive'][jj]),
                            al=len(near(Vc, jj, vt, 8)), en=len(near(Vc, jj, 1 - vt, 8)), en5=len(near(Vc, jj, 1 - vt, 5)),
                            hp=Vc['hp'][jj] / Vc['maxHp'][jj] if Vc['alive'][jj] else 0, fV=Vc['foc'][jj], fE=Ec['foc'][jj],
                            gV=Vc['gems'][jj], gE=Ec['gems'][jj], hpE=Ec['hp'][jj] / Ec['maxHp'][jj] if Ec['alive'][jj] else 0,
                            stun=Vc['stun'][j] or 0, stunev=r in stun_ev.get(Vc['id'], ()), chan=Vc['chan'][jj] or 0,
                            seesE=Ec['id'] in (Vc['sees'][j] or []), seenByE=Ec['id'] in (Vc['seenBy'][j] or []),
                            dsp=dist_sp[vt][pv[0]][pv[1]] if pv else None, onsp=bool(pv and on_spawn(pv, spawn[vt]))))
        out['death'] = dict(vt=vt, rd=rd, by=e['by'], byPrism=e['by'] == Ec['id'], gems=e['gems'], cause=e['cause'],
                            assists=e.get('assists', []), at=e['at'], vwin=(vt == winner), win=win,
                            killer_type=next(mc for mc in meta['champions'] if mc['id'] == e['by'])['name'])
    # Q3 contact onsets: both Prisms alive and the distance drops to <= 6 (new onset only > 5 rounds after the last)
    ons = []
    prev_close = False
    for i in range(N):
        a, b = pos(pr[0], i), pos(pr[1], i)
        close = bool(a and b and cheb(a, b) <= 6)
        if close and not prev_close:
            if not ons or rounds[i] - ons[-1]['r'] > 5:
                r = rounds[i]
                ons.append(dict(r=r, b=[br.get((pr[t]['id'], r), '?') for t in (0, 1)], f=[pr[t]['foc'][i] for t in (0, 1)],
                                hp=[pr[t]['hp'][i] / pr[t]['maxHp'][i] for t in (0, 1)],
                                dsp=[dist_sp[t][(a, b)[t][0]][(a, b)[t][1]] for t in (0, 1)],
                                al=[len(near(pr[t], i, t, 8)) for t in (0, 1)],
                                died=[bool(death_of(pr[t]['id'], r, r + 20)) for t in (0, 1)]))
        prev_close = close
    out['onsets'] = ons
    return out

if __name__ == '__main__':
    idx = json.load(open(ANA / 'index.json'))['games']
    dirs = sorted({g['dir'] for g in idx if g.get('ok', True)})
    if len(sys.argv) > 1: dirs = dirs[:int(sys.argv[1])]
    with Pool(32) as p:
        res = [r for r in p.imap_unordered(one, dirs, chunksize=4) if r]
    pickle.dump(res, open('research/mx-rhea/scripts/pd_rows.pkl', 'wb'))
    print(len(res), 'games', sum(len(r['episodes']) for r in res), 'episodes', sum(1 for r in res if r['death']), 'deaths')
