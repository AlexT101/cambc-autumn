"""Opening simulator: our team farms its half of a map from round 1; plans are per-body target lists.
Used to estimate how much a solved team plan beats per-body greedy, by value at a horizon."""
import json, collections, random, math, sys, os
import numpy as np

CAMP = {'wolf': (1350, 20, 3, 40, 4, 40), 'elk': (2400, 60, 4, 90, 15, 60), 'golem': (5000, 120, 4, 160, 36, 80),
        'gem_cluster': (120, 0, 0, 0, 7, 50), 'gold_cluster': (120, 0, 0, 20, 0, 50), 'monolith': (20000, 200, 5, 300, 200, 150)}
# camp dps (base stats; basic x attack-reset, damage spells per 8 rounds), ranged, health, gold bonus
def T(dps, rng, hp, bonus=1.0): return dict(dps=dps, range=rng, hp=hp, bonus=bonus)
TYPES = {'Ryth': T(45 * 1.125 + 100 / 8, 1, 1200), 'Vesper Vale': T(35 * 1.125, 3, 1000, 1.33), 'Prism': T(35 + 2.5 * 90 / 8, 3, 700),
         'Stellar': T(30 + 3.4 * 85 / 8, 3, 650), 'Vendetta': T(65 * 1.125, 1, 900), 'Marcella': T(40 * 1.125 + 2 * 60 / 8, 1, 1200),
         'Tavi': T(45 * 1.125 + 1.6 * 110 / 8, 3, 900), 'Willow': T(55 * 1.125, 3, 700), 'Ren': T(35 + 1.1 * 100 / 8, 1, 900),
         'Varg': T(50 * 1.125, 1, 1000), 'Heart of Ruin': T(30 * 1.125 + 1.5 * 80 / 8, 1, 1000),
         'Cassi': T(30 + 2 * 100 / 8, 3, 600), 'Issac': T(45 * 1.125, 1, 900)}
CAP = 6
HEAL_FRAC = 0.4  # usable share of health before a trip home

def bodies_of(picks):
    out = []
    for p in picks:
        if p == 'Cassi & Issac': out += ['Cassi', 'Issac']
        else: out.append(p)
    return out

class Map:
    def __init__(self, m, side):
        self.name = m['file']; W, H = m['width'], m['height']; self.W, self.H = W, H
        block = np.zeros((W, H), bool)
        for x, y in m['walls'] + m['holes'] + m['altars']: block[x, y] = True
        camps = [(c['x'], c['y'], c['type']) for c in m['camps']]
        for x, y, _ in camps: block[x, y] = True
        sa = m['spawn'][0]
        A = [(x, y) for x in range(sa['minX'], sa['maxX']) for y in range(sa['minY'], sa['maxY'])]  # max exclusive
        sym = m['symmetry']
        mir = (lambda p: (W - 1 - p[0], p[1])) if sym == 'horizontal' else (lambda p: (p[0], H - 1 - p[1])) if sym == 'vertical' else (lambda p: (W - 1 - p[0], H - 1 - p[1]))
        Bt = [mir(p) for p in A]
        us_t, them_t = (A, Bt) if side == 'a' else (Bt, A)
        for p in them_t: block[p] = True
        self.block = block
        # groups: cardinal components of camp tiles
        at = {(x, y): t for x, y, t in camps}; seen = set(); self.groups = []
        for p in at:
            if p in seen: continue
            comp = []; st = [p]; seen.add(p)
            while st:
                q = st.pop(); comp.append(q)
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    r = (q[0] + d[0], q[1] + d[1])
                    if r in at and r not in seen: seen.add(r); st.append(r)
            mem = [(at[q],) + CAMP[at[q]] for q in comp]
            g = dict(tiles=comp, members=mem, hp=sum(x[1] for x in mem), gold=sum(x[4] for x in mem), gems=sum(x[5] for x in mem),
                     respawn=max(x[6] for x in mem), mono=any(x[0] == 'monolith' for x in mem))
            self.groups.append(g)
        self.spawn = us_t; self.espawn = them_t
        self.f_spawn = self.bfs(self.spawn)
        eb = block.copy()
        for p in self.espawn: eb[p] = False
        self.f_espawn = self.bfs(self.espawn, eb)
        INF = 10 ** 6
        for g in self.groups:
            ring = set()
            for (x, y) in g['tiles']:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        q = (x + dx, y + dy)
                        if 0 <= q[0] < W and 0 <= q[1] < H and not block[q]: ring.add(q)
            g['ring'] = list(ring)
            g['d_us'] = min([self.f_spawn[q] for q in ring] or [INF]); g['d_them'] = min([self.f_espawn[q] for q in ring] or [INF])
        # ours: reachable, not monolith, nearer us (ties in)
        self.ours = [i for i, g in enumerate(self.groups) if g['d_us'] < INF and not g['mono'] and g['gold'] + g['gems'] > 0 and g['d_us'] <= g['d_them']]
        self.D = {}
        for i in self.ours:
            f = self.bfs(self.groups[i]['ring'])
            self.D[i] = {j: min(f[q] for q in self.groups[j]['ring']) for j in self.ours}
            self.D[i]['spawn'] = min(f[q] for q in self.spawn)

    def bfs(self, src, block=None):
        block = self.block if block is None else block
        W, H = self.W, self.H; INF = 10 ** 6
        f = np.full((W, H), INF, np.int32); dq = collections.deque()
        for p in src: f[p] = 0; dq.append(p)
        while dq:
            x, y = dq.popleft(); d = f[x, y] + 1
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    a, b = x + dx, y + dy
                    if 0 <= a < W and 0 <= b < H and not block[a, b] and f[a, b] > d: f[a, b] = d; dq.append((a, b))
        return f

def reach(dist, rng): return max(0, dist - (rng - 1)) if dist > 0 else 0

def simulate(mp, team, plans, H, p_gold=0.3, trace=False):
    """plans: per body an ordered list of groups. A free body takes the first listed group that is
    standing (not captured and not respawning) or being cleared. Returns value paid by round H."""
    n = len(team)
    grp = {i: dict(hp=float(mp.groups[i]['hp']), back=0, cleared_at=None) for i in mp.ours}
    # body state: location ('spawn' or group), free_at, damage taken, target, index into plan
    B = [dict(loc='spawn', t=0.0, dmg=0.0, tgt=None, k=0) for _ in range(n)]
    value = 0.0; caps = []
    t = 0.0
    # events: process bodies in order of t
    present = collections.defaultdict(set)   # group -> bodies hitting
    arrive = {}
    def eta(b, g):
        loc = B[b]['loc']
        d = mp.groups[g]['d_us'] if loc == 'spawn' else mp.D[loc][g]
        return reach(d, team[b]['range'])
    def choose(b, now):
        lst = plans[b]
        while B[b]['k'] < len(lst):
            g = lst[B[b]['k']]
            if grp[g]['cleared_at'] is None and grp[g]['back'] <= now + eta(b, g): return g
            B[b]['k'] += 1
        return None
    # discrete time stepping (1 round) is simple and exact enough
    for b in range(n):
        g = choose(b, 0)
        if g is not None: B[b]['tgt'] = g; arrive[b] = eta(b, g)
        else: B[b]['tgt'] = None
    holder_until = {}
    for r in range(1, H + 1):
        # captures paid
        for g, (pay, hb) in list(holder_until.items()):
            if r >= pay:
                G = mp.groups[g]; v = G['gems'] + p_gold * G['gold'] * team[hb]['bonus']
                value += v; caps.append((r, g, hb, v)); del holder_until[g]
                grp[g]['back'] = r + G['respawn']; grp[g]['hp'] = float(G['hp']); grp[g]['cleared_at'] = None
                B[hb]['loc'] = g; B[hb]['tgt'] = None; B[hb]['t'] = r
        # bodies arriving / acting
        hitting = collections.defaultdict(list)
        for b in range(n):
            if B[b]['tgt'] is None:
                if B[b]['t'] > r or any(hb == b for _, hb in holder_until.values()): continue
                g = choose(b, r)
                if g is None: continue
                B[b]['tgt'] = g; arrive[b] = r + eta(b, g)
            g = B[b]['tgt']
            if grp[g]['cleared_at'] is not None:  # someone else finished it
                B[b]['loc'] = g; B[b]['tgt'] = None; B[b]['k'] += 1; B[b]['t'] = r; continue
            if r >= arrive[b] and grp[g]['back'] <= r: hitting[g].append(b)
        for g, bs in hitting.items():
            G = mp.groups[g]; gs = grp[g]
            dps = sum(team[b]['dps'] for b in bs)
            before = gs['hp']; gs['hp'] -= dps
            # camp damage: alive attackers (deadliest-first order) hit the tank (melee first, else first listed)
            killed = G['hp'] - max(0.0, gs['hp']); acc = 0; strength = 0
            for m in sorted(G['members'], key=lambda m: -m[2] / m[1]):
                acc += m[1]
                if acc > killed: strength += m[2]
            tank = min(bs, key=lambda b: (team[b]['range'], -team[b]['hp']))
            B[tank]['dmg'] += strength
            if gs['hp'] <= 0:
                gs['cleared_at'] = r
                hb = max(bs, key=lambda b: (team[b]['bonus'], -b))
                holder_until[g] = (r + CAP, hb)
                for b in bs:
                    B[b]['loc'] = g; B[b]['tgt'] = None; B[b]['k'] += 1; B[b]['t'] = r + 1
            for b in bs:
                if B[b]['dmg'] > HEAL_FRAC * team[b]['hp'] and B[b]['tgt'] is not None or (B[b]['dmg'] > HEAL_FRAC * team[b]['hp'] and gs['hp'] <= 0 and b != holder_until.get(g, (0, -1))[1]):
                    # home to heal: recall (5) or walk, then from spawn
                    home = min(mp.D[g]['spawn'], 6)
                    B[b]['loc'] = 'spawn'; B[b]['t'] = r + home + 1; B[b]['dmg'] = 0; B[b]['tgt'] = None
    if trace: return value, caps
    return value

def greedy_plan(mp, team, H, joint=False, p_gold=0.3):
    """Sequential claims: each body in id order takes the best rate group not claimed (solo clears), then
    keeps choosing from where that group is, as a list."""
    n = len(team); plans = [[] for _ in range(n)]; claimed = set()
    loc = ['spawn'] * n; tfree = [0.0] * n
    for _ in range(12):
        for b in sorted(range(n), key=lambda b: tfree[b]):
            best = None
            for g in mp.ours:
                if g in claimed: continue
                G = mp.groups[g]
                d = G['d_us'] if loc[b] == 'spawn' else mp.D[loc[b]][g]
                rounds = reach(d, team[b]['range']) + G['hp'] / team[b]['dps'] + CAP
                v = (G['gems'] + p_gold * G['gold'] * team[b]['bonus']) / rounds
                if best is None or v > best[0]: best = (v, g, rounds)
            if best is None: continue
            plans[b].append(best[1]); claimed.add(best[1]); loc[b] = best[1]; tfree[b] += best[2]
    return plans

def improve(mp, team, H, plans, iters=3000, seed=0, p_gold=0.3):
    rnd = random.Random(seed)
    best = [list(p) for p in plans]; bv = simulate(mp, team, best, H, p_gold)
    n = len(team); G = mp.ours
    if not G: return best, bv
    for it in range(iters):
        cand = [list(p) for p in best]
        op = rnd.random(); b = rnd.randrange(n)
        if op < 0.3:  # insert a group at a position
            cand[b].insert(rnd.randrange(len(cand[b]) + 1), rnd.choice(G))
        elif op < 0.5 and cand[b]:  # remove
            del cand[b][rnd.randrange(len(cand[b]))]
        elif op < 0.7 and len(cand[b]) > 1:  # swap
            i, j = rnd.sample(range(len(cand[b])), 2); cand[b][i], cand[b][j] = cand[b][j], cand[b][i]
        elif op < 0.85:  # copy another body's step (joint clear)
            c = rnd.randrange(n)
            if cand[c]:
                g = cand[c][rnd.randrange(len(cand[c]))]; cand[b].insert(rnd.randrange(len(cand[b]) + 1), g)
        else:  # replace a step
            if cand[b]: cand[b][rnd.randrange(len(cand[b]))] = rnd.choice(G)
        v = simulate(mp, team, cand, H, p_gold)
        if v > bv or (v == bv and sum(map(len, cand)) < sum(map(len, best))): best, bv = cand, v
    return best, bv

if __name__ == '__main__':
    maps = {json.loads(l)['file']: json.loads(l) for l in open(os.path.expanduser('~/tmp-offload/draftfarm/ana/ladder.jsonl'))}
    picks = {}
    for l in open('/home/ubuntu/cambc-autumn/research/ladder-scrims-2026-11-06/data/games.jsonl'):
        g = json.loads(l)
        if g['version'] == 87 and g.get('our_picks'): picks[(g['map'].replace('_', '-'), g['side'])] = g['our_picks']
    name, side = sys.argv[1], sys.argv[2]; H = int(sys.argv[3])
    mp = Map(maps[name], side); team = [TYPES[x] for x in bodies_of(picks[(name, side)])]
    gp = greedy_plan(mp, team, H); gv, gc = simulate(mp, team, gp, H, trace=True)
    bp, bv = improve(mp, team, H, gp)
    print(name, side, bodies_of(picks[(name, side)]), 'ours', len(mp.ours), 'greedy', round(gv), 'improved', round(bv))
    print(' greedy', gp, gc); print(' best', bp, simulate(mp, team, bp, H, trace=True)[1])
