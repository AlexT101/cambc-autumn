"""Fish on its own spawn with enemies about: staying in, fighting from it, and respawns.

Rows: tactic_rows.py `spawn` (alive turn start on Fish's spawn, a visible enemy within 10) and
`spawn0` (same, no visible enemy within 10). Completed, not channelling, with an off-spawn
neighbour free (else leaving is impossible). Label `left`: the turn ends off the spawn.
ehd = Chebyshev distance from the nearest visible enemy to the nearest tile of Fish's spawn.

Rule (fit on FIT by grid over k): leave iff no visible enemy within k of the spawn and health
is full (hp == max: on spawn it heals to full at each turn end, so short of full means it was
hit or just arrived).
"""
import argparse
import collections

from tactic_common import FIT, HELD, NAMES, Score, rows, write


def prep():
    out = []
    for r in rows(['spawn']):
        if not r['done'] or r['ch'] != 0 or not r['end']:
            continue
        offs = [x for x in r['exits'] if not x['home']]
        if not offs:
            continue
        home = {tuple(x['p']) for x in r['exits'] if x['home']} | {tuple(r['pos'])}
        r['left'] = tuple(r['end']) not in home
        r['ehd'] = min(e['ohome_d'] for e in r['enemies'])
        out.append(r)
    return out


def rule(r, k):
    return r['ehd'] > k and r['hpf'] >= 0.999


def main(out):
    data = prep()
    res = {}
    fit = [r for r in data if r['cohort'] in FIT]
    grid = {k: sum(rule(r, k) == r['left'] for r in fit) for k in range(0, 11)}
    k = max(grid, key=grid.get)
    res['grid_fit'] = grid
    sc = Score(f'spawn: leave iff no enemy within {k} of spawn and full health')
    dist_only = Score(f'spawn: leave iff no enemy within {k} of spawn')
    rates = collections.Counter()
    for r in data:
        sc.add(r, rule(r, k), r['left'], False, dict(ehd=r['ehd'], hpf=round(r['hpf'], 3)))
        dist_only.add(r, r['ehd'] > k, r['left'], False)
        rates[f"ehd={min(r['ehd'], 8)}", r['left']] += 1
        rates[f"hp {'full' if r['hpf'] >= 0.999 else 'short'}", r['left']] += 1
        # Fighting from the spawn edge: an enemy in this turn's reach.
        if any(e['mine'] > 0 for e in r['enemies']):
            rates['reachable', 'hit'] += bool(r['hit_ids'])
            rates['reachable', 'n'] += 1
            rates['reachable', 'hit and stayed'] += bool(r['hit_ids']) and not r['left']
    print(sc.line()); print(dist_only.line())
    res['rule'] = sc.report(); res['distance_only'] = dist_only.report()
    res['leave_rates'] = {kk: [rates[kk, True], rates[kk, True] + rates[kk, False]] for kk in sorted({a for a, _ in rates if a != 'reachable'})}
    res['fight_from_spawn'] = dict(n=rates['reachable', 'n'], hit=rates['reachable', 'hit'],
                                   hit_and_stayed=rates['reachable', 'hit and stayed'])
    # No-enemy baseline: the same health rule.
    base = collections.Counter()
    nb = Score('spawn0 (no enemy): leave iff full health')
    short = Score('spawn or spawn0, short of full health: stays on spawn')
    for r in data:
        if r['hpf'] < 0.999:
            short.add(r, False, r['left'], False, dict(hpf=round(r['hpf'], 3)))
    for r in rows(['spawn0']):
        if not r['end']:
            continue
        nb.add(r, r['hpf'] >= 0.999, r['left'], False)
        if r['hpf'] < 0.999:
            short.add(r, False, r['left'], False, dict(hpf=round(r['hpf'], 3)))
        base[f"hp {'full' if r['hpf'] >= 0.999 else 'short'}", r['left']] += 1
        if r['since_resp'] is not None and r['since_resp'] <= 2:
            base['respawn turn+1', r['left']] += 1
    print(nb.line()); print(short.line())
    res['short_health_stays'] = short.report()
    res['no_enemy'] = dict(rule=nb.report(), leave_rates={kk: [base[kk, True], base[kk, True] + base[kk, False]]
                                                           for kk in sorted({a for a, _ in base})})
    # Respawn with enemies near: the first turns after a respawn.
    resp = collections.Counter()
    for r in data:
        if r['since_resp'] is not None and r['since_resp'] <= 3:
            resp['n'] += 1; resp['left'] += r['left']; resp['hit'] += bool(r['hit_ids'])
            resp['enemy within 4 of spawn'] += r['ehd'] <= k
            resp['left with enemy within k'] += r['left'] and r['ehd'] <= k
    res['respawn'] = dict(resp)
    print('respawn', dict(resp))
    write(out, res)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    main(p.parse_args().out)
