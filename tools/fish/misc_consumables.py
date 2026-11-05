"""Fish's altar locks and teleport crystals (MISC.md section 2-3).

    python3 tools/fish/misc_consumables.py OUT.json

1. Lock maps. A game "uses locks" if any Fish champion places one (all five cohorts) or buys one
   (item logs, four oldest). Static feature: walking distance (king steps; walls, holes and altars
   block, camps do not) from each spawn region to a tile within 1 of each altar; the altar nearest
   our spawn by that distance gives gap = enemy distance - own distance. Rule: uses locks iff
   gap <= 4. The threshold is read off the four oldest cohorts' maps; maps seen only in the fifth
   cohort are the held-out check.
2. Lock placement: which altar (rank by our walking distance), placing distance, carried gems,
   own tribute start at that altar within the next 3 own turns, visible enemy tribute at it.
3. Teleports: Chebyshev hop length, walking distance between the ends, repeated hops.
"""
import argparse, sys
from collections import Counter, defaultdict, deque
sys.path.insert(0, 'tools/fish')
from misc_common import *


def walk(st, src, extra=()):
    W, H = st['W'], st['H']
    bl = {tuple(t) for t in st['walls']} | {tuple(t) for t in st['holes']} | {tuple(a) for a in st['altars']} | set(extra)
    D = {t: 0 for t in src}; q = deque(src)
    while q:
        p = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (p[0] + dx, p[1] + dy)
                if 0 <= n[0] < W and 0 <= n[1] < H and n not in bl and n not in D: D[n] = D[p] + 1; q.append(n)
    return D


def adist(D, a):
    return min(D.get((a[0] + dx, a[1] + dy), 10 ** 6) for dx in (-1, 0, 1) for dy in (-1, 0, 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('out'); a = ap.parse_args()
    logs = item_logs()
    maps = {}  # map -> {'gap', 'cohorts', 'uses': set, 'buy_place_agree'}
    place = Counter(); place_ex = defaultdict(list); tele = Counter(); hops = Counter(); tele_ex = []
    agree = Counter()
    for g in games():
        st, c = g['static'], g['cohort']
        own = [tuple(t) for t in st['own']]; foe = [tuple(t) for t in st['foe']]
        if g['map'] not in maps:
            Do, Df = walk(st, own), walk(st, foe)
            rank = sorted((adist(Do, t), adist(Df, t), tuple(t)) for t in st['altars'])
            maps[g['map']] = {'gap': rank[0][1] - rank[0][0] if rank else None, 'near': rank[0][:2] if rank else None,
                              'altars': len(rank), 'rank': [r[2] for r in rank], 'cohorts': set(), 'uses': set()}
        M = maps[g['map']]; M['cohorts'].add(c)
        placed = any(x['k'] == 'Place altar lock' for r in g['rows'] for x in r['a'])
        ids = {r['id'] for r in g['rows']}
        if all((g['game'], i) in logs for i in ids):
            boughtl = any(e['cons'].get('Altar lock', 0) > 0 for i in ids for e in logs[(g['game'], i)])
            agree[(boughtl, placed)] += 1
            M['uses'].add(boughtl)
        else:
            M['uses'].add(placed)
        for aid, rows in by_actor(g['rows']).items():
            for i, r in enumerate(rows):
                p = (r['s'].get('x'), r['s'].get('y'))
                for j, x in enumerate(r['a']):
                    if x['k'] == 'Move': p = tuple(x['to'])
                    if x['k'] == 'Place altar lock':
                        t = tuple(x['to'])
                        later = [y for y in r['a'][j + 1:]] + [y for rr in rows[i + 1:i + 4] for y in rr['a']]
                        trib = any(y['k'] == 'Submit gems' and y.get('b') and cheb(y['b'][:2], t) <= 1 for y in later)
                        etrib = any(e[7] == 2 and cheb((e[2], e[3]), t) <= 1 for e in r['en'])
                        k = (f"rank{M['rank'].index(t)}", f'dist{cheb(p, t)}', 'gems>0' if r['s']['gems'] else 'gems0',
                             'own-tribute-at-it<=3turns' if trib else 'no-own-tribute', 'enemy-tributing-there' if etrib else '-')
                        place[k] += 1
                        if len(place_ex[k]) < 3: place_ex[k].append((g['game'], r['r'], aid, r['name']))
                    if x['k'] == 'Teleport channel':
                        t = tuple(x['to']); d = walk(st, [p], extra=foe).get(t, 10 ** 6)
                        tele[('cheb', cheb(p, t))] += 1
                        tele[('walk', 'unreachable_or>=40' if d >= 40 else '12-39' if d >= 12 else str(d))] += 1
                        hops[(g['map'], p, t)] += 1
                        if d < 12 and len(tele_ex) < 10: tele_ex.append((g['game'], r['r'], aid, r['name'], p, t, d))
    # Lock-map rule.
    old = {m: v for m, v in maps.items() if v['cohorts'] - {'fifth'}}
    new = {m: v for m, v in maps.items() if not (v['cohorts'] - {'fifth'})}
    def score(ms, th):
        ok = bad = 0; errs = []
        for m, v in ms.items():
            if len(v['uses']) != 1 or v['gap'] is None: continue
            pred = v['gap'] <= th; act = next(iter(v['uses']))
            if pred == act: ok += 1
            else: bad += 1; errs.append((m, v['gap'], v['near'], act))
        return ok, ok + bad, errs
    sweep = {th: score(old, th)[:2] for th in range(0, 10)}
    res = {'doc': __doc__,
           'buy_vs_place_per_game': {f'bought={k[0]},placed={k[1]}': v for k, v in agree.items()},
           'maps_mixed_usage': [m for m, v in maps.items() if len(v['uses']) != 1],
           'gap_threshold_sweep_old_maps': sweep,
           'rule_gap<=4_old_maps': score(old, 4), 'rule_gap<=4_fifth_only_maps': score(new, 4),
           'baseline_always_lock_old': [sum(1 for v in old.values() if v['uses'] == {True}), len(old)],
           'baseline_always_lock_fifth_only': [sum(1 for v in new.values() if v['uses'] == {True}), len(new)],
           'maps': {m: {'gap': v['gap'], 'near': v['near'], 'altars': v['altars'], 'uses': sorted(v['uses']), 'cohorts': sorted(v['cohorts'])} for m, v in sorted(maps.items())},
           'placement': {' | '.join(k): [n, place_ex[k]] for k, n in place.most_common()},
           'teleport': {' '.join(map(str, k)): n for k, n in sorted(tele.items(), key=str)},
           'teleport_distinct_hops': [len(hops), sum(hops.values())], 'teleport_top_hops': [[*k, n] for k, n in hops.most_common(10)],
           'teleport_short_walk_examples': tele_ex}
    print('buy/place agreement', dict(agree)); print('sweep', sweep)
    print('gap<=4 old', res['rule_gap<=4_old_maps'][:2], 'fifth-only', res['rule_gap<=4_fifth_only_maps'][:2])
    print('errors', res['rule_gap<=4_old_maps'][2], res['rule_gap<=4_fifth_only_maps'][2])
    print('baselines', res['baseline_always_lock_old'], res['baseline_always_lock_fifth_only'])
    for k, n in place.most_common(14): print(n, k)
    print(sum(place.values()), 'placements'); print(dict(tele)); print(res['teleport_distinct_hops'])
    write_result(a.out, res)


if __name__ == '__main__':
    main()
