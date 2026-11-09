"""Retreat audit: ocean's retreat episodes (D-line branch R) against a worst-case pursuit model.

Per episode (first R turn with a visible enemy within 8 = r0), pursuers = those enemies. Model, per our turn k
(k=1 is our turn in r0, tile q_k after it): a melee pursuer hits if q_k is within 1 of a tile it reaches in k
turns; a ranged one if within 3 of a tile it reaches in k-1 turns (a ranged walk spends the attack). Pursuers
dash once when ready. Our own spawn ends exposure (the turn end heals). Exposure = sum over turns of pursuers in
reach. DP gives the least exposure to reach spawn within H turns: walking only, with our dash, and along
shortest walking paths only; compared with ocean's actual tiles under the same model.
usage: python3 retreat_audit.py EXTRACT_DIR OUT.jsonl [--bot ocean]"""
import sys, json, gzip, zipfile
import numpy as np
from concurrent.futures import ProcessPoolExecutor

DASHERS = {1, 2, 4, 9, 12}  # Vesper, Vendetta, Issac, Ren, Heart of Ruin: dash is slot 1
RANGED = {1, 3, 5, 6, 8, 11}
NAMES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
CAMP_RANGE = {'Wolf': 3, 'Elk': 4, 'Golem': 4, 'Monolith': 5}
INF = 1e9
DIRS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]


def shift_or(A, dx, dy):
    B = np.zeros_like(A)
    H, W = A.shape
    ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
    xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
    B[yd, xd] = A[ys, xs]
    return B


def dil(A, r=1):
    for _ in range(r):
        B = A.copy()
        for dx, dy in DIRS:
            if dx or dy: B |= shift_or(A, dx, dy)
        A = B
    return A


def shift_min(E, dx, dy):
    B = np.full_like(E, INF)
    H, W = E.shape
    ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
    xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
    B[yd, xd] = E[ys, xs]
    return B


def mmin(E):  # min over staying and the 8 king steps
    B = E.copy()
    for dx, dy in DIRS:
        if dx or dy: B = np.minimum(B, shift_min(E, dx, dy))
    return B


def dash_min(E, passable, walk):
    one = mmin(E)
    mid = np.where(passable, one, INF)
    two = mmin(mid)
    return np.where(walk, np.minimum(one, two), INF)


def dash_set(A, passable, walk):
    one = dil(A)
    return (one | dil(one & passable)) & walk


def bfs(start, walk, cap=200):
    """Walking distance field (king steps) from a bool start set."""
    D = np.full(walk.shape, -1, dtype=np.int32)
    cur = start & walk if (start & walk).any() else start.copy()
    D[cur] = 0
    seen = cur.copy()
    for k in range(1, cap):
        nxt = dil(cur) & walk & ~seen
        if not nxt.any(): break
        D[nxt] = k
        seen |= nxt
        cur = nxt
    return D


def load_stdout_decisions(src, team_letter):
    z = zipfile.ZipFile(src)
    dec = {}
    for line in z.read(f'team-{team_letter}.stdout').decode(errors='replace').splitlines():
        if line.startswith('D '):
            p = line.split()
            if len(p) >= 4: dec[(int(p[1]), int(p[2]))] = p[3]
    return dec


def analyse(args):
    ex, g, bot = args
    meta = json.load(open(f"{ex}/{g['dir']}/meta.json"))
    M = json.load(open(f"{ex}/maps/{g['mapHash']}.json"))
    R = json.load(gzip.open(f"{ex}/{g['dir']}/rounds.json.gz"))
    ev = [json.loads(l) for l in gzip.open(f"{ex}/{g['dir']}/events.jsonl.gz", 'rt')]
    Wd, Hd = M['width'], M['height']
    grid = lambda pts: (lambda A: ([A.__setitem__((p[1], p[0]), True) for p in pts], A)[1])(np.zeros((Hd, Wd), bool))
    wall, hole, bush, altar = grid(M['walls']), grid(M['holes']), grid(M['bushes']), grid(M['altars'])
    spawn = [np.zeros((Hd, Wd), bool) for _ in range(2)]
    for t in range(2):
        s = M['spawn'][t]
        spawn[t][s['minY']:s['maxY'] + 1, s['minX']:s['maxX'] + 1] = True
    groups = M['groups']
    camp_by_id = {c['id']: c for c in M['camps']}
    # group state rows, forward-filled per round
    gstate = {}
    rows = sorted(R.get('groups', []), key=lambda r: r[0])
    cols = R.get('groupCols')
    bush_cluster = np.full((Hd, Wd), -1, dtype=np.int32)
    nb = 0
    for y in range(Hd):
        for x in range(Wd):
            if bush[y, x] and bush_cluster[y, x] < 0:
                st = [(x, y)]; bush_cluster[y, x] = nb
                while st:
                    cx, cy = st.pop()
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < Wd and 0 <= ny < Hd and bush[ny, nx] and bush_cluster[ny, nx] < 0:
                            bush_cluster[ny, nx] = nb; st.append((nx, ny))
                nb += 1
    rounds = R['round']
    ridx = {r: i for i, r in enumerate(rounds)}
    ch = {c['id']: c for c in R['champions']}
    team_of = {c['id']: c['team'] for c in meta['champions']}
    type_of = {c['id']: c['type'] for c in meta['champions']}
    teams = g['teams']
    deaths = {}
    killer = {}
    for e in ev:
        if e['k'] == 'death' and e.get('linked') is None:
            deaths.setdefault(e['v'], []).append(e['r'])
            killer[(e['v'], e['r'])] = (e.get('by'), e.get('camp'), e.get('gems', 0))
    # forward-filled awake/state per group: list of (round, state, awake)
    ghist = {}
    for r in rows:
        ghist.setdefault(r[1], []).append((r[0], r[2], r[6]))

    def gat(gid, rnd):
        st, aw = 1, 0
        for (rr, s, a) in ghist.get(gid, []):
            if rr > rnd: break
            st, aw = s, a
        return st, aw

    by_round = {}
    for e in ev: by_round.setdefault(e['r'], []).append(e)

    def evs_by_round_range(a, b):
        for rr in range(a, b + 1):
            yield from by_round.get(rr, [])

    out = []
    src = g['source']
    for t in (0, 1):
        if teams[t] != bot: continue
        letter = 'ab'[t]
        try:
            dec = load_stdout_decisions(src, letter)
        except KeyError:
            continue
        mine = [c for c in ch if team_of[c] == t]
        foes = [c for c in ch if team_of[c] != t]
        for c in mine:
            A = ch[c]
            Rr = sorted(r for (r, h) in dec if h == c and dec[(r, h)] == 'R')
            # episodes: R rounds with gaps <= 2
            eps = []
            for r in Rr:
                if eps and r - eps[-1][1] <= 3: eps[-1][1] = r
                else: eps.append([r, r])
            for (r0, r1) in eps:
                i0 = ridx.get(r0 - 1)
                if i0 is None or not A['alive'][i0]: continue
                p0 = (A['x'][i0], A['y'][i0])
                if p0[0] is None or p0[0] < 0: continue
                sees = A['sees'][ridx[r0]] if ridx.get(r0) is not None else []
                purs = []
                for f in foes:
                    B = ch[f]
                    if not B['alive'][i0] or B['x'][i0] is None or B['x'][i0] < 0: continue
                    q = (B['x'][i0], B['y'][i0])
                    if f in sees and max(abs(q[0] - p0[0]), abs(q[1] - p0[1])) <= 8:
                        purs.append((f, q))
                if not purs: continue
                # outcome: death between r0 and r1+3
                died = None
                for dr in deaths.get(c, []):
                    if r0 <= dr <= r1 + 3: died = dr; break
                # blocked camp tiles at r0
                camp_block = np.zeros((Hd, Wd), bool)
                for gi, gr in enumerate(groups):
                    st, aw = gat(gr['id'], r0)
                    if st == 1:
                        for cid in gr['camps']:
                            cc = camp_by_id[cid]; camp_block[cc['y'], cc['x']] = True
                walk_us = ~(wall | hole | altar | camp_block | spawn[1 - t])
                pass_us = ~(wall | camp_block | spawn[1 - t])
                walk_them = ~(wall | hole | altar | camp_block | spawn[t])
                pass_them = ~(wall | camp_block | spawn[t])
                home = bfs(spawn[t], ~(wall | hole | altar | camp_block | spawn[1 - t]) | spawn[t])
                hd0 = int(home[p0[1], p0[0]])
                if hd0 < 0: continue
                # actual path first: K turns until death, spawn, or the episode's end + 3
                path, reached, died_k = [], None, None
                for rr in range(r0, r1 + 4):
                    ii = ridx.get(rr)
                    if ii is None: break
                    if not A['alive'][ii] or A['x'][ii] is None or A['x'][ii] < 0:
                        died_k = len(path) + 1 if died else None
                        break
                    q = (A['x'][ii], A['y'][ii])
                    path.append((rr, ii, q))
                    if spawn[t][q[1], q[0]]: reached = len(path); break
                K = len(path) + (1 if died_k else 0)
                Hn = max(1, K)
                expo = np.zeros((Hn + 1, Hd, Wd), np.float32)
                for (f, q) in purs:
                    ft = type_of[f]
                    cdE = ch[f]['cd1'][i0] if ft in DASHERS else 99
                    P0 = np.zeros((Hd, Wd), bool); P0[q[1], q[0]] = True
                    P1 = np.zeros((Hd, Wd), bool)
                    sets = [P0 | P1]
                    for k in range(1, Hn + 1):
                        nP0 = dil(P0) & walk_them | P0
                        nP1 = dil(P1) & walk_them | P1
                        if ft in DASHERS and k >= cdE + 1:
                            nP1 |= dash_set(nP0, pass_them, walk_them) | (dil(dash_set(P0, pass_them, walk_them)) & walk_them)
                        P0, P1 = nP0, nP1
                        sets.append(P0 | P1)
                    for k in range(1, Hn + 1):
                        expo[k] += dil(sets[k - 1], 3) if ft in RANGED else dil(sets[k], 1)
                expo[:, spawn[t]] = 0
                cdU = A['cd1'][i0] if type_of[c] in DASHERS else 99
                ok_us = walk_us | spawn[t]

                def solve(use_dash):
                    """Least exposure over Hn turns, by the home distance reached: returns {slack: exposure}."""
                    E0 = np.full((Hd, Wd), INF); E0[p0[1], p0[0]] = 0
                    E1 = np.full((Hd, Wd), INF)
                    for k in range(1, Hn + 1):
                        w0 = np.where(ok_us, mmin(E0), INF)
                        w1 = np.where(ok_us, mmin(E1), INF)
                        if use_dash and k >= cdU + 1:
                            d = np.minimum(dash_min(w0, pass_us, ok_us), np.where(ok_us, mmin(dash_min(E0, pass_us, ok_us)), INF))
                            w1 = np.minimum(w1, d)
                        E0, E1 = w0 + expo[k], w1 + expo[k]
                    E = np.minimum(E0, E1)
                    res = {}
                    for s, lim in ((0, max(0, hd0 - Hn)), (2, max(0, hd0 - Hn) + 2), (4, max(0, hd0 - Hn) + 4), ('act', end_home), ('any', 10 ** 6)):
                        keep = (home >= 0) & (home <= lim)
                        v = float(E[keep].min()) if keep.any() else INF
                        res[s] = v if v < INF / 2 else None
                    return res
                end_home = int(home[path[-1][2][1], path[-1][2][0]]) if path else hd0
                if end_home < 0: end_home = hd0
                ow = solve(False)
                od = solve(type_of[c] in DASHERS) if type_of[c] in DASHERS else ow
                odr = od
                if type_of[c] in DASHERS and cdU > 0:
                    saved = cdU; cdU = 0; odr = solve(True); cdU = saved
                # turns the victim could not or did not walk
                stunned = sum(1 for (rr, ii, q) in path if (A['stun'][ii - 1] or 0) > 0 or A['turn'][ii] == 5)
                chan = sum(1 for (rr, ii, q) in path if A['chan'][ii] in (1, 2))
                still, prev = 0, p0
                for (rr, ii, q) in path:
                    still += q == prev; prev = q
                # first-step agreement: is ocean's first tile on some optimal walking path? (exposure at turn 1)
                first_expo = float(expo[1][path[0][2][1], path[0][2][0]]) if path else None
                min_first = None
                if path:
                    nb = [float(expo[1][p0[1] + dy, p0[0] + dx]) for dx, dy in DIRS
                          if 0 <= p0[0] + dx < Wd and 0 <= p0[1] + dy < Hd and ok_us[p0[1] + dy, p0[0] + dx]]
                    min_first = min(nb) if nb else None
                act = sum(float(expo[k + 1][q[1], q[0]]) for k, (_, _, q) in enumerate(path))
                rlast = r0 + K - 1
                taken = 0.0
                for e in evs_by_round_range(r0, rlast):
                    if e['k'] in ('attack', 'cast') and e.get('a') in team_of and team_of[e['a']] != t:
                        for vid, amt in e.get('dmg', []) or []:
                            if vid == c: taken += amt
                bush_avail = bush_used = wake_opp = 0
                cur = p0
                rng = 3 if type_of[c] in RANGED else 1
                for (rr, ii, q) in path:
                    pursuer_pos = [(ch[f]['x'][ii - 1], ch[f]['y'][ii - 1]) for (f, _) in purs
                                   if ch[f]['alive'][ii - 1] and ch[f]['x'][ii - 1] is not None and ch[f]['x'][ii - 1] >= 0]
                    hidden_nb = False
                    for dx, dy in DIRS:
                        nx, ny = cur[0] + dx, cur[1] + dy
                        if 0 <= nx < Wd and 0 <= ny < Hd and bush[ny, nx] and walk_us[ny, nx]:
                            cl = bush_cluster[ny, nx]
                            if all(not (0 <= e[0] < Wd and 0 <= e[1] < Hd and bush_cluster[e[1], e[0]] == cl) for e in pursuer_pos):
                                hidden_nb = True
                    bush_avail += hidden_nb
                    found = False
                    for gr in groups:
                        st, aw = gat(gr['id'], rr - 1)
                        if st != 1 or aw != 0: continue
                        for cid in gr['camps']:
                            cc = camp_by_id[cid]
                            cr = CAMP_RANGE.get(cc['type'])
                            if cr is None: continue
                            dm = max(abs(cc['x'] - cur[0]), abs(cc['y'] - cur[1]))
                            if dm <= rng and any(max(abs(cc['x'] - e[0]), abs(cc['y'] - e[1])) <= min(cr, dm - 1) for e in pursuer_pos):
                                found = True; break
                        if found: break
                    wake_opp += found
                    cur = q
                    bush_used += bool(bush[q[1], q[0]])
                # allies near at r0
                ally_d = [max(abs(ch[a]['x'][i0] - p0[0]), abs(ch[a]['y'][i0] - p0[1])) for a in mine
                          if a != c and ch[a]['alive'][i0] and ch[a]['x'][i0] is not None and ch[a]['x'][i0] >= 0]
                kb = killer.get((c, died)) if died else None
                out.append(dict(map=g['map'], src=src, team=t, opp=teams[1 - t], champ=c, type=NAMES[type_of[c]], r0=r0, r1=r1,
                                hp=A['hp'][i0], maxhp=A['maxHp'][i0], gems=A['gems'][i0], home=hd0, cdU=cdU if cdU != 99 else None,
                                purs=[NAMES[type_of[f]] for f, _ in purs], pdist=[max(abs(q[0] - p0[0]), abs(q[1] - p0[1])) for _, q in purs],
                                pdash=[type_of[f] in DASHERS for f, _ in purs],
                                opt_walk=ow, opt_dash=od, opt_dash_ready=odr, stunned=stunned, chan=chan, still=still, first_expo=first_expo, min_first=min_first, K=K, act=act, taken=taken, act_reached=reached, end_home=end_home, died=died, died_k=died_k,
                                killer=(NAMES[type_of[kb[0]]] if kb and kb[0] in type_of else ('camp' if kb and kb[1] is not None else None)),
                                bush_avail=bush_avail, bush_used=bush_used, wake_opp=wake_opp,
                                ally_min=min(ally_d) if ally_d else None, allies8=sum(d <= 8 for d in ally_d),
                                n_bushes=int(bush.sum())))
    return out


if __name__ == '__main__':
    ex, outp = sys.argv[1], sys.argv[2]
    bot = sys.argv[sys.argv.index('--bot') + 1] if '--bot' in sys.argv else 'ocean'
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    games = [g for g in json.load(open(f'{ex}/index.json'))['games'] if g.get('ok') and bot in g['teams']]
    seen = set(); uniq = []
    for g in games:
        if g['dir'] in seen: continue
        seen.add(g['dir']); uniq.append(g)
    if limit: uniq = uniq[:limit]
    n = 0
    with open(outp, 'w') as f, ProcessPoolExecutor(int(sys.argv[sys.argv.index('--procs') + 1]) if '--procs' in sys.argv else 8) as pool:
        for rows in pool.map(analyse, [(ex, g, bot) for g in uniq], chunksize=1):
            for r in rows: f.write(json.dumps(r) + '\n'); n += 1
    print('episodes', n, 'games', len(uniq))
