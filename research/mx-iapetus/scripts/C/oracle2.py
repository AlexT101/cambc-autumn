# Does what a team knows of the enemy predict whether a group is approached by an enemy before the team could
# finish it? Per (team, sampled round, available group): static weight bin, the expected margin (enemies stay
# where last seen; dead ones walk from their spawn after respawning), the provable margin (last seen less the
# rounds since, no recall) and the oracle outcome (no enemy within 4 + radius before the finish).
import json, gzip, sys, collections, numpy as np
sys.argv = sys.argv[:1] + sys.argv[1:]
from oracle import mapinfo, A
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 200
idx = json.load(open(A + 'index.json'))['games']
dirs = sorted({r['dir'] for r in idx})[:LIMIT]
T = collections.defaultdict(lambda: [0, 0, 0])  # key -> [n, free, gems sum when free]
def add(k, free, gems):
    v = T[k]; v[0] += 1; v[1] += free; v[2] += gems * free
def mbin(m):
    for b in (-20, -10, 0, 10, 20, 40):
        if m < b: return '<%d' % b
    return '>=40'
for d in dirs:
    m = json.load(open(A + d + '/meta.json'))
    G = mapinfo(A + m['mapFile'].replace('../', ''))
    gid = {g['id']: i for i, g in enumerate(G)}
    R = json.load(gzip.open(A + d + '/rounds.json.gz'))
    N = len(R['round']); ch = R['champions']
    X = np.array([[(-999 if v is None else v) for v in c['x']] for c in ch]); Y = np.array([[(-999 if v is None else v) for v in c['y']] for c in ch])
    AL = np.array([c['alive'] for c in ch], dtype=bool); TM = np.array([c['team'] for c in ch])
    RS = np.array([[(0 if v is None else v) for v in c['respawn']] for c in ch])
    ST = np.array([c['str'] for c in ch], dtype=float)
    ids = [c['id'] for c in ch]; pos_of = {cid: k for k, cid in enumerate(ids)}
    SEEN = np.zeros((len(ch), N), dtype=np.int8)  # bit t: seen by team t
    for k, c in enumerate(ch):
        for j, lst in enumerate(c['seenBy']):
            for o in lst or []:
                if o in pos_of: SEEN[k, j] |= 1 << int(TM[pos_of[o]])
    ng = len(G); state = np.zeros((ng, N), dtype=np.int8); ghp = np.zeros((ng, N)); grsp = np.zeros((ng, N))
    rows = collections.defaultdict(list)
    for row in R['groups']: rows[row[1]].append(row)
    for g, rs in rows.items():
        if g not in gid: continue
        i = gid[g]; last = None; k = 0; rs.sort(key=lambda r: r[0])
        for j in range(N):
            rr = R['round'][j]
            while k < len(rs) and rs[k][0] <= rr: last = rs[k]; k += 1
            if last is not None: state[i, j] = last[2]; ghp[i, j] = last[7]; grsp[i, j] = last[5]
    for t in (0, 1):
        en = np.where(TM != t)[0]; us = np.where(TM == t)[0]
        nxt = np.full((ng, N + 1), 10**6, dtype=np.int64)
        for i, g in enumerate(G):
            cx, cy = g['c']; near = np.zeros(N, dtype=bool)
            for e in en: near |= AL[e] & (np.maximum(np.abs(X[e] - cx), np.abs(Y[e] - cy)) <= 4 + g['rad'])
            for j in range(N - 1, -1, -1): nxt[i, j] = j if near[j] else nxt[i, j + 1]
        last_pos = {e: None for e in en}; last_j = {e: -1 for e in en}
        for j in range(N):
            for e in en:
                if AL[e, j] and (SEEN[e, j] >> t & 1): last_pos[e] = (X[e, j], Y[e, j]); last_j[e] = j
                if not AL[e, j]: last_pos[e] = None
            if j % 3: continue
            alive_us = [u for u in us if AL[u, j]]
            if not alive_us: continue
            dead = sum(1 for e in en if not AL[e, j])
            for i, g in enumerate(G):
                if g['mono'] or g['gems'] <= 0: continue
                h = g['home'][t]
                s = state[i, j]
                if s not in (1, 2, 3): continue
                cx, cy = g['c']
                near = min(max(abs(X[u, j] - cx), abs(Y[u, j] - cy)) for u in alive_us)
                wait = grsp[i, j] if s == 3 else 0
                if wait > near + 10: continue
                strength = max(ST[u, j] for u in alive_us)
                hp = g['hp'] if s == 3 else ghp[i, j]
                F = int(max(near, wait) + hp / max(strength, 30) + 6)
                free = int(nxt[i, j] > j + F)
                spawn_steps = g['steps'][1 - t]
                exp_arr = []; prov_arr = []
                for e in en:
                    reach = 4 + g['rad']
                    if not AL[e, j]:
                        a = RS[e, j] + 1 + spawn_steps - reach; exp_arr.append(a); prov_arr.append(a)
                    elif last_pos[e] is None:
                        a = spawn_steps - reach; exp_arr.append(a); prov_arr.append(0)  # unknown since respawn: at spawn
                    else:
                        dd = max(abs(last_pos[e][0] - cx), abs(last_pos[e][1] - cy)) - reach
                        exp_arr.append(dd); prov_arr.append(dd - (j - last_j[e]))
                me = min(exp_arr) - F; mp = min(prov_arr) - F
                hb = 'h<.25' if h < .25 else 'h<.5' if h < .5 else 'h<1' if h < .999 else 'h=1'
                add(('all', hb), free, g['gems'])
                add(('exp', hb, mbin(me)), free, g['gems'])
                add(('prov', hb, mbin(mp)), free, g['gems'])
                add(('dead', hb, min(dead, 3)), free, g['gems'])
print('games', len(dirs))
for k in sorted(T, key=str):
    n, f, gs = T[k]
    if n >= 200: print('%-28s n %7d  free %5.1f%%' % (k, n, 100 * f / n))
