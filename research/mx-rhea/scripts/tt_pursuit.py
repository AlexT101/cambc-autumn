"""Pursuits: maximal runs of a champion's turns on one farm group (debug D lines), over every mirror game, with what
the run produced (hits on the group, a capture share, arrival), how it ended (the group's true state, enemies seen,
an ally on it, a retreat or death), its F/R flips, and recall-to-farm trips (RFCHOOSE -> landing -> what it did).
Writes a pickle of rows for tt_sum.py. Usage: py tt_pursuit.py ANALYSIS_DIR BATCH_DIR OUT.pkl"""
import gzip, json, sys, zipfile, pickle
from collections import defaultdict, deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path('/home/ubuntu/wt/mx-rhea')


def fields(mp):
    W, H = mp['width'], mp['height']
    block = set(map(tuple, mp['walls'])) | set(map(tuple, mp['holes'])) | set(map(tuple, mp['altars']))
    out = {}
    for g in mp['groups']:
        D = [[-1] * H for _ in range(W)]
        q = deque()
        for t in g['tiles']:
            D[t[0]][t[1]] = 0; q.append(tuple(t))
        while q:
            x, y = q.popleft(); d = D[x][y] + 1
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and D[nx][ny] < 0 and (nx, ny) not in block:
                        D[nx][ny] = d; q.append((nx, ny))
        out[g['id']] = D
    return out


def game(args):
    d, src = args
    g = ROOT / 'replays/ana-mirror' / d
    try:
        meta = json.loads((g/'meta.json').read_text())
        R = json.load(gzip.open(g/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(g/'events.jsonl.gz', 'rt')]
        mp = json.loads((g/meta['mapFile']).resolve().read_text())
        z = zipfile.ZipFile(ROOT / src)
    except Exception as e:
        return None
    winner = meta['result']['winner']
    champs = meta['champions']
    team_of = {c['id']: c['team'] for c in champs}
    name = {c['id']: c['name'] for c in champs}
    D = {}; RF = defaultdict(list)
    for side in 'ab':
        try: txt = z.read(f'team-{side}.stdout').decode(errors='replace')
        except KeyError: continue
        for l in txt.splitlines():
            l = l.lstrip('\x00'); p = l.split()
            if not p: continue
            if p[0] == 'D' and len(p) >= 6:
                D[(int(p[1]), int(p[2]))] = (p[3], int(p[4]))
            elif p[0] in ('RFCHOOSE', 'RFLAND', 'RFDROP', 'RFLOST', 'RFDEAD') and len(p) >= 4:
                RF[int(p[2])].append((p[0], int(p[1]), int(p[3])))
    if not D: return None
    F = fields(mp)
    G = {x['id']: x for x in mp['groups']}
    camp_g = {c['id']: c['group'] for c in mp['camps']}
    ri = {r: i for i, r in enumerate(R['round'])}
    nR = len(R['round'])
    # group state per round index (forward-filled): (state, team, respawn)
    gst = {gid: [None] * nR for gid in G}
    rows_by_g = defaultdict(list)
    for row in R['groups']: rows_by_g[row[1]].append(row)
    for gid, rows in rows_by_g.items():
        if gid not in gst: continue
        rows.sort(); j = 0; cur = None
        for i, r in enumerate(R['round']):
            while j < len(rows) and rows[j][0] <= r: cur = rows[j]; j += 1
            gst[gid][i] = (cur[2], cur[3], cur[5], cur[6]) if cur else None
    hits = defaultdict(set)   # (cid, round) -> groups hit
    cap = {}                  # (cid, round) -> (g, gems)
    caps_team = defaultdict(list)  # g -> [(round, team)]
    deaths = {}
    for e in ev:
        if e['k'] in ('attack', 'cast') and 'camp' in e and 'a' in e:
            hits[(e['a'], e['r'])].add(camp_g.get(e['camp']))
        elif e['k'] == 'capture':
            caps_team[e['g']].append((e['r'], e['team']))
            for s in e['shares']: cap[(s[0], e['r'])] = (e['g'], s[1])
        elif e['k'] == 'death':
            deaths[(e['v'], e['r'])] = (e.get('by'), e['gems'])
    C = {c['id']: c for c in R['champions']}
    # per-team capture gems a champion-round alive (income rate) up to r600
    inc = {}
    for t in (0, 1):
        gems = sum(s[1] for e in ev if e['k'] == 'capture' and e['team'] == t and e['r'] <= 600 for s in e['shares'])
        alive = sum(sum(C[c['id']]['alive'][:min(nR, 600)]) for c in champs if c['team'] == t)
        inc[t] = gems / max(1, alive)
    out = []
    rfout = []
    last_round = R['round'][-1]
    for c in champs:
        cid, team = c['id'], c['team']
        cr = C[cid]
        seq = []
        for i, r in enumerate(R['round']):
            k = D.get((r, cid))
            if k is None: continue
            alive = cr['alive'][i]
            pos = (cr['x'][i], cr['y'][i]) if alive else None
            seq.append((r, i, k[0], k[1], alive, pos, cr['gems'][i], cr['hp'][i], cr['maxHp'][i], tuple(cr['sees'][i] or ())))
        # pursuits: maximal runs with the same farm group >= 0, alive
        j = 0
        while j < len(seq):
            r, i, br, fg, alive, pos, *_ = seq[j]
            if fg < 0 or not alive or fg not in G:
                j += 1; continue
            k = j
            while k + 1 < len(seq) and seq[k+1][3] == fg and seq[k+1][4]: k += 1
            run = seq[j:k+1]
            Fg = F[fg]
            def dd(p):
                return Fg[p[0]][p[1]] if p else -1
            d0 = dd(run[0][5]); d1 = dd(run[-1][5]); dmin = min((dd(x[5]) for x in run if x[5] and dd(x[5]) >= 0), default=-1)
            nh = sum(1 for x in run if fg in hits.get((cid, x[0]), ()))
            share = sum(cap[(cid, x[0])][1] for x in run if (cid, x[0]) in cap and cap[(cid, x[0])][0] == fg)
            # also a share paid the round after the run ends (capture phase precedes turns)
            nxt = run[-1][0] + 1
            if (cid, nxt) in cap and cap[(cid, nxt)][0] == fg: share += cap[(cid, nxt)][1]
            brs = [x[2] for x in run]
            flips = sum(1 for a, b in zip(brs, brs[1:]) if a == 'F' and b == 'R')
            nR_ = brs.count('R'); nF = brs.count('F'); nK = sum(1 for b in brs if b in 'Kk'); nP = sum(1 for b in brs if b in 'PQ')
            st0 = gst[fg][run[0][1]]; st1 = gst[fg][run[-1][1]]
            seen = set()
            for x in run: seen |= set(x[9])
            seen_end = set(run[-1][9])
            # what came next
            if k + 1 < len(seq):
                nx = seq[k+1]
                nxt_br, nxt_fg, nxt_alive = nx[2], nx[3], nx[4]
            else:
                nxt_br, nxt_fg, nxt_alive = 'end', -1, 1
            p0, p1 = run[0][5], run[-1][5]
            adv_next = None
            if nxt_fg in F and p0 and p1:
                a0, a1 = F[nxt_fg][p0[0]][p0[1]], F[nxt_fg][p1[0]][p1[1]]
                if a0 >= 0 and a1 >= 0: adv_next = a0 - a1
            died = any((cid, rr) in deaths for rr in range(run[0][0], run[-1][0] + 2))
            # team capture of fg within the run (+3 rounds)
            r0, r1 = run[0][0], run[-1][0]
            tcap = [t for (rr, t) in caps_team.get(fg, []) if r0 <= rr <= r1 + 3]
            # an ally standing within 1 of the group's tiles at the end
            ally_on = 0
            for a in champs:
                if a['team'] != team or a['id'] == cid: continue
                ar = C[a['id']]
                ie = run[-1][1]
                if ar['alive'][ie] and Fg[ar['x'][ie]][ar['y'][ie]] >= 0 and Fg[ar['x'][ie]][ar['y'][ie]] <= 2: ally_on += 1
            out.append(dict(game=d, team=team, win=int(team == winner), cid=cid, name=name[cid], g=fg, side=G[fg]['side'],
                            rel='mid' if G[fg]['side'] == -1 else ('own' if G[fg]['side'] == team else 'enemy'),
                            gems=G[fg]['gems'], gold=G[fg]['gold'], mono=any(t == 'Monolith' for t in G[fg]['types']),
                            strength=any(t in ('Wolf', 'Elk', 'Golem', 'Monolith') for t in G[fg]['types']),
                            r0=r0, r1=r1, n=len(run), d0=d0, d1=d1, dmin=dmin, hits=nh, share=share,
                            flips=flips, nR=nR_, nF=nF, nK=nK, nP=nP, st0=st0, st1=st1, seen=len(seen), seen_end=len(seen_end),
                            nxt_br=nxt_br, nxt_fg=nxt_fg, died=died, tcap=tcap, ally_on=ally_on, bag=run[0][6],
                            hp0=run[0][7] / max(1, run[0][8]), p0=p0, p1=p1, adv_next=adv_next, rounds=last_round, inc=inc[team], ncamp=len(G)))
            j = k + 1
        # recall-to-farm trips
        chooses = [x for x in RF[cid] if x[0] == 'RFCHOOSE']
        lands = {x[1]: x[2] for x in RF[cid] if x[0] == 'RFLAND'}
        for rl, gl in lands.items():
            # first farm group after landing, and whether it reached gl
            i0 = ri.get(rl)
            if i0 is None: continue
            fgs = [D.get((rr, cid), ('?', -9))[1] for rr in range(rl, rl + 6)]
            Fg = F.get(gl)
            reached = None
            for rr in range(rl, min(last_round, rl + 60) + 1):
                ii = ri.get(rr)
                if ii is None or not cr['alive'][ii]: break
                if D.get((rr, cid), ('?', -9))[1] != gl: break
                if Fg and Fg[cr['x'][ii]][cr['y'][ii]] <= 4: reached = rr - rl; break
            rfout.append(dict(game=d, team=team, win=int(team == winner), cid=cid, name=name[cid], r=rl, g=gl,
                              kept=sum(1 for f in fgs if f == gl), first=fgs[1] if len(fgs) > 1 else -9, reached=reached,
                              side=G[gl]['side'] if gl in G else -2))
    return out, rfout


def main():
    ana, batch, outp = sys.argv[1], sys.argv[2], sys.argv[3]
    idx = json.load(open(Path(ana)/'index.json'))['games']
    seen = {}
    for r in idx:
        if r['dir'] not in seen and Path(ROOT/r['source']).exists(): seen[r['dir']] = r['source']
    rows, rfs = [], []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(game, list(seen.items()), chunksize=4):
            if o: rows.extend(o[0]); rfs.extend(o[1])
    pickle.dump((rows, rfs), open(outp, 'wb'))
    print(len(seen), 'games', len(rows), 'pursuits', len(rfs), 'recall-to-farm landings')


if __name__ == '__main__':
    main()
