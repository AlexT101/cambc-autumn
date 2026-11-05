"""Fish shopping: where it shops, how much it buys, and when it buys altar locks (MISC.md section 1-2).

    python3 tools/fish/misc_shop.py OUT.json

Inputs: misc_rows.py rows (all five cohorts) and drafts-emblems-games.json.gz item logs (four
oldest cohorts). Rules tested, each per cohort:
  A. Fish shops at turn start iff dead, or alive on a tile of its "spawn box": the own spawn
     rectangle minus its far row and column in team A's frame (x < maxX and y < maxY), mirrored
     for team B. Turns: alive and starting on the real spawn, gold >= 30.
  B. Dead with gold >= 30: shops. Alive off spawn: never shops.
  C. A shop turn buys consumables first, then floor((gold - 10 x consumables) / 30) shards.
  D. Locks: per map, used in every game or none; on a lock map, bought iff not carrying one and
     (gold - 10 x crystals) mod 30 >= 10: crystal first, then the lock from what shards leave.
"""
import argparse, math, sys
from collections import Counter, defaultdict
sys.path.insert(0, 'tools/fish')
from misc_common import *


def mirror(st, t):
    W, H, s = st['W'], st['H'], st['symmetry']
    x, y = t
    return (W - 1 - x, y) if s == 'horizontal' else (x, H - 1 - y) if s == 'vertical' else (W - 1 - x, H - 1 - y)


def box(st, side):
    """Fish's spawn box: tiles of the real spawn except team A's max-x column and max-y row."""
    a = [tuple(t) for t in (st['own'] if side == 0 else st['foe'])]
    x1, y1 = max(t[0] for t in a), max(t[1] for t in a)
    inner = {t for t in a if t[0] < x1 and t[1] < y1}
    return inner if side == 0 else {mirror(st, t) for t in inner}


def bought(entries):
    """Shards bought (an emblem's formation counts its shards), locks, crystals, from one turn's log."""
    sh = lk = cr = 0
    for x in entries:
        if x['kind'] != 'Shop': continue
        for k, v in x['items'].items():
            sh += v * (25 if 'Greed' in k else 5) if 'Emblem' in k else v
        lk += max(0, x['cons'].get('Altar lock', 0)); cr += max(0, x['cons'].get('Teleport crystal', 0))
    return sh, lk, cr


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('out'); a = p.parse_args()
    logs = item_logs()
    R = defaultdict(Counter); EX = defaultdict(list)

    def tally(key, cohort, ok, ex):
        R[key][(cohort, ok)] += 1
        if not ok and len(EX[key]) < 12: EX[key].append(ex)

    lockmap = defaultdict(set)  # map -> {game used locks?}
    lockrows = []
    for g in games():
        st, side, c = g['static'], g['side'], g['cohort']
        fb = box(st, side)
        acts = by_actor(g['rows'])
        haslog = all((g['game'], i) in logs for i in acts)
        if haslog:
            lockmap[g['map']].add(any(e['cons'].get('Altar lock', 0) > 0 for i in acts for e in logs[(g['game'], i)]))
        for aid, rows in acts.items():
            byr = defaultdict(list)
            for e in logs.get((g['game'], aid), []): byr[e['r']].append(e)
            lock = 0
            for r in rows:
                s, e = r['s'], r['e']
                shop = any(x['k'] == 'Shop' for x in r['a'])
                ex = (g['game'], r['r'], aid, r['name'], s.get('gold'))
                if shop:
                    ks = [x['k'] for x in r['a']]
                    tally('shop_before_any_move_or_attack', c, all(k in ('Cancel channel', 'Set priority', 'Shop') for k in ks[:ks.index('Shop')]), ex)
                    tally('gold_after_shop_below_30', c, e['gold'] < 30, ex + (e['gold'],))
                if s['alive'] and r['spawn0'] and s['gold'] >= 30:
                    pos = (s['x'], s['y'])
                    tally('A_shop_iff_in_spawn_box', c, shop == (pos in fb), ex + (pos, pos in fb))
                    tally('A_baseline_always_shop_on_spawn', c, shop, ex)
                if not s['alive'] and s['gold'] >= 30: tally('B_dead_gold30_shops', c, shop, ex)
                if s['alive'] and not r['spawn0'] and not r['spawn1']: tally('B_alive_off_spawn_never_shops', c, not shop, ex)
                if shop and haslog:
                    sh, lk, cr = bought(byr.get(r['r'], []))
                    g0 = s['gold']
                    tally('C_shards_eq_floor_after_consumables', c, sh == math.floor((g0 - 10 * (lk + cr)) / 30), ex + (sh, lk, cr))
                    tally('C_gold_accounting', c, abs(g0 - 30 * sh - 10 * (lk + cr) - e['gold']) < 1e-6, ex)
                    left = g0 - 30 * math.floor(g0 / 30)
                    lockrows.append((g['map'], c, g['game'], r['r'], aid, r['name'], lock, left, lk, cr, g0))
                for x in byr.get(r['r'], []): lock += x['cons'].get('Altar lock', 0)
    # D. lock maps, then the purchase rule on lock maps (crystal turns reported apart).
    consistent = sum(1 for v in lockmap.values() if len(v) == 1)
    R['D_map_consistent'][('all', True)] = consistent; R['D_map_consistent'][('all', False)] = len(lockmap) - consistent
    for (m, c, game, rnd, aid, name, carrying, left, lk, cr, g0) in lockrows:
        if lockmap[m] != {True} or carrying: continue
        left = (g0 - 10 * cr) % 30  # a crystal is paid for first
        tally('D_lock_iff_leftover10', c, bool(lk) == (left >= 10), (game, rnd, aid, name, g0, left, lk, cr))
        if cr: tally('D_lock_iff_leftover10_crystal_turns', c, bool(lk) == (left >= 10), (game, rnd, aid, name, g0, left, lk, cr))
    out = {'rules': __doc__, 'results': {}, 'counterexamples': EX,
           'lock_maps': {m: sorted(v) for m, v in sorted(lockmap.items())}}
    for k, v in sorted(R.items()):
        per = {}
        for coh in sorted({x[0] for x in v}):
            per[coh] = [v[(coh, True)], v[(coh, True)] + v[(coh, False)]]
        tot = [sum(x[0] for x in per.values()), sum(x[1] for x in per.values())]
        out['results'][k] = {'per_cohort': per, 'total': tot}
        print(f'{k:45s} total {pct(*tot)}  ' + '  '.join(f'{coh} {x[0]}/{x[1]}' for coh, x in per.items()))
    write_result(a.out, out)


if __name__ == '__main__':
    main()
