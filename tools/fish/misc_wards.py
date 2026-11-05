"""Fish's wards (MISC.md section 4).

    python3 tools/fish/misc_wards.py OUT.json [--vision-games 40]

1. Cadence: rounds between an actor's consecutive placements (10 = placed the turn it recharges).
2. Geometry: Chebyshev distance from the actor's tile at placement (after its walk; turns with a
   cast or teleport before the ward are skipped), and the tile kind (bush/open).
3. Collisions: a "Movement blocked" event 2 tiles from the actor is a failed ward attempt onto an
   unseen allied ward (rules wards.placement) if the tile holds a teammate's current ward.
4. Tile score (vision, first N games of the model and fifth cohorts): new bush tiles = bush tiles in
   the ward's 13x13 shadowcast not already seen by the actor (its own 17x17 sight and its current
   ward's). Is the chosen tile in the argmax over legal tiles within 2 (failed attempts removed)?
   Baseline: the mean share of legal tiles in the argmax (a uniformly random legal tile).
   Readiness: with the ward recharged, is a ward placed, by best score > 0 or = 0.
"""
import argparse, sys
from collections import Counter, defaultdict
from multiprocessing import Pool
sys.path.insert(0, 'tools/fish'); sys.path.insert(0, 'tools/replay/narrative')
from misc_common import *
from vision import Vision


def clusters(bushes):
    B = {tuple(b) for b in bushes}; cid = {}; k = 0
    for b in B:
        if b in cid: continue
        st = [b]; cid[b] = k
        while st:
            p = st.pop()
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (p[0] + d[0], p[1] + d[1])
                if n in B and n not in cid: cid[n] = k; st.append(n)
        k += 1
    return cid


def turn_ward(r):
    """(position before the ward, ward tile or None, failed 2-tile attempts, clean = no cast/teleport first)."""
    p = (r['s'].get('x'), r['s'].get('y')); clean = True; tried = []
    for a in r['a']:
        if a['k'] == 'Move': p = tuple(a['to'])
        if a['k'] in ('Cast ability', 'Teleport channel'): clean = False
        if a['k'] == 'Movement blocked' and p[0] is not None and cheb(p, a['to']) == 2: tried.append(tuple(a['to']))
        if a['k'] == 'Place ward': return p, tuple(a['to']), tried, clean
    return p, None, tried, clean


def basic(g):
    st = g['static']; bush = {tuple(b) for b in st['bushes']}
    C = Counter(); ex = defaultdict(list)
    wards = {}; last = {}
    for r in g['rows']:  # chronological
        if not r['s']['alive']: continue
        aid = r['id']
        p, t, tried, clean = turn_ward(r)
        for x in tried:
            hit = any(w == x for i, w in wards.items() if i != aid)
            C[('blocked2', 'on-teammate-ward' if hit else 'other')] += 1
            if not hit and len(ex['blocked2-other']) < 8: ex['blocked2-other'].append((g['game'], r['r'], aid, r['name'], p, x))
        if tried: C[('blocked-turn-then', 'placed' if t else 'gave-up')] += 1
        if t is None: continue
        if aid in last: C[('gap', min(r['r'] - last[aid], 60))] += 1
        else: C[('first', min(r['r'] // 10 * 10, 200))] += 1
        last[aid] = r['r']
        if clean and p[0] is not None:
            C[('dist', cheb(p, t))] += 1
            C[('tile', 'bush' if t in bush else 'open')] += 1
            C[('enemy-visible', bool(r['ne']), 'bush' if t in bush else 'open')] += 1
        wards[aid] = t
    return g['cohort'], C, ex


def vision_game(g):
    st = g['static']; W, H = st['W'], st['H']
    walls = {tuple(t) for t in st['walls']}; holes = {tuple(t) for t in st['holes']}
    alts = {tuple(a) for a in st['altars']}; foe = {tuple(t) for t in st['foe']}
    bc = clusters(st['bushes']); V = Vision(W, H, walls, bc); bush = set(bc)
    C = Counter(); share = []; ex = []
    for aid, rows in by_actor(g['rows']).items():
        lastr = -99; wt = None
        for r in rows:
            if not r['s']['alive']: continue
            p, t, tried, clean = turn_ward(r)
            ready = r['r'] - lastr >= 10
            w0 = wt
            if t: lastr, wt = r['r'], t
            if not ready or not clean or p[0] is None: continue
            mine = V.fov(p, 8) | (V.fov(w0, 6) if w0 else frozenset())
            sc = {}
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    c = (p[0] + dx, p[1] + dy)
                    if 0 <= c[0] < W and 0 <= c[1] < H and c not in walls and c not in holes and c not in alts and c not in foe and c not in tried:
                        sc[c] = len((V.fov(c, 6) - mine) & bush)
            if not sc: continue
            best = max(sc.values())
            C[('ready', 'placed' if t else 'not', 'best>0' if best > 0 else 'best=0')] += 1
            C[('ready', 'attempted' if t or tried else 'none', 'best>0' if best > 0 else 'best=0')] += 1
            if tried:  # the first, failed attempt is the tile Fish wanted: score it with nothing removed
                full = dict(sc)
                for c in tried: full[c] = len((V.fov(c, 6) - mine) & bush)
                fb = max(full.values())
                if fb > 0: C[('first-attempt-in-argmax', full[tried[0]] == fb)] += 1
            if t and best > 0:
                am = [c for c in sc if sc[c] == best]
                C[('chosen-in-argmax', t in am)] += 1
                C[('chosen-unique-argmax', am == [t])] += 1
                share.append(len(am) / len(sc))
                if t not in am and len(ex) < 6: ex.append((g['game'], r['r'], aid, r['name'], p, t, sc.get(t), best))
    return g['cohort'], C, share, ex


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('out'); ap.add_argument('--vision-games', type=int, default=40)
    a = ap.parse_args()
    per = defaultdict(Counter); EX = defaultdict(list)
    vis = []; cnt = Counter()
    for g in games():
        coh, C, ex = basic(g); per[coh] += C
        for k, v in ex.items(): EX[k] += v[:2]
        if g['cohort'] in ('model', 'fifth') and cnt[g['cohort']] < a.vision_games:
            cnt[g['cohort']] += 1; vis.append(g)
    with Pool(6) as P: vres = P.map(vision_game, vis)
    V = defaultdict(Counter); shares = defaultdict(list); vex = []
    for coh, C, sh, ex in vres: V[coh] += C; shares[coh] += sh; vex += ex
    tot = sum(per.values(), Counter())
    def j(c): return {' '.join(map(str, k)): v for k, v in sorted(c.items(), key=str)}
    res = {'doc': __doc__, 'per_cohort': {k: j(v) for k, v in per.items()}, 'total': j(tot), 'examples': EX,
           'vision': {k: j(v) for k, v in V.items()}, 'vision_games': dict(cnt),
           'vision_random_baseline': {k: sum(v) / len(v) for k, v in shares.items() if v}, 'vision_misses': vex}
    gaps = sum(v for k, v in tot.items() if k[0] == 'gap')
    print('gap 10:', pct(tot[('gap', 10)], gaps), ' gap<=12:', pct(sum(tot[('gap', x)] for x in (10, 11, 12)), gaps), ' gap>=60:', pct(tot[('gap', 60)], gaps))
    dn = sum(v for k, v in tot.items() if k[0] == 'dist'); print('dist2:', pct(tot[('dist', 2)], dn), 'bush:', pct(tot[('tile', 'bush')], dn))
    bn = tot[('blocked2', 'on-teammate-ward')] + tot[('blocked2', 'other')]
    print('blocked at 2 on a teammate ward:', pct(tot[('blocked2', 'on-teammate-ward')], bn), ' then placed:', tot[('blocked-turn-then', 'placed')], 'gave up:', tot[('blocked-turn-then', 'gave-up')])
    for coh, C in V.items():
        n = C[('chosen-in-argmax', True)] + C[('chosen-in-argmax', False)]
        print(coh, 'in argmax', pct(C[('chosen-in-argmax', True)], n), 'unique', pct(C[('chosen-unique-argmax', True)], n), 'random', round(res['vision_random_baseline'].get(coh, 0), 3),
              'first-attempt in argmax', C[('first-attempt-in-argmax', True)], '/', C[('first-attempt-in-argmax', True)] + C[('first-attempt-in-argmax', False)],
              'attempted best>0', C[('ready', 'attempted', 'best>0')], 'none', C[('ready', 'none', 'best>0')], 'attempted best=0', C[('ready', 'attempted', 'best=0')], 'none', C[('ready', 'none', 'best=0')],
              'ready placed best>0', C[('ready', 'placed', 'best>0')], 'not', C[('ready', 'not', 'best>0')], '| best=0 placed', C[('ready', 'placed', 'best=0')], 'not', C[('ready', 'not', 'best=0')])
    write_result(a.out, res)


if __name__ == '__main__':
    main()
