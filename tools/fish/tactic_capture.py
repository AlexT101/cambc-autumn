"""Fish on (or beside) an empty camp group while enemy champions are near.

Rows: tactic_rows.py `cap` (completed turns, not in a tribute/teleport channel, a visible enemy
within 8, an empty group within 3). Capture state is the actor's own read of the group:
captureTeam == Fish's side -> our hold, timer = rounds to payout; 2 -> contested.

Contexts (one decision per row and group):
- hold:      Fish stands on the group, no enemy on it (our hold, or about to start). Label: ends on it.
- contested: Fish and an enemy both on it. Label: Fish ends on it.
- enemy-held: Fish 1 tile from the group, an enemy on it, no ally on it. Label: Fish steps on.
Acceptable (COMBAT.md rule, own tile, unfitted): kill available or (hp/max > 0.49 and danger <= 0.28).
Rules are fit on FIT cohorts by grid search and scored on HELD.
"""
import argparse
import collections

from tactic_common import FIT, HELD, NAMES, Score, rows, write


def acceptable(r, h=0.49, z=0.28):
    kill = any(e['mine'] >= e['hp'] + e['sh'] for e in r['enemies'])
    return kill or (r['hpf'] > h and r['danger0'] <= z)


def contexts(r):
    out = []
    for n in r['near']:
        st = n['state']
        timer = st[3] if st[2] == r['side'] else None
        if n['on'] and not n['en_on']:
            out.append(('hold', n, timer))
        elif n['on'] and n['en_on']:
            out.append(('contested', n, timer))
        elif n['d'] == 1 and n['en_on'] and not n['al_on']:
            out.append(('enemy-held', n, timer))
    return out


def hold_rule(r, timer, h, z, tmax):
    # Stay unless the hold has not started counting down (timer 5 / none) and the tile is unacceptable.
    if timer is not None and timer <= tmax:
        return True
    return acceptable(r, h, z)


def main(out):
    data = collections.defaultdict(list)
    for r in rows(['cap']):
        if not r['done'] or r['ch'] in (2, 3, 4):
            continue
        for name, n, timer in contexts(r):
            data[name].append((r, n, timer))
    res = {}
    # Hold.
    hold = data['hold']
    fit = [x for x in hold if x[0]['cohort'] in FIT]
    grid = [(h, z, t) for h in (0.3, 0.4, 0.45, 0.49, 0.55, 0.6) for z in (0.2, 0.28, 0.4, 0.6, 1.0)
            for t in (0, 1, 2, 3, 4)]
    best = max(grid, key=lambda g: sum(hold_rule(r, tm, *g) == n['end_on'] for r, n, tm in fit))
    sc = Score(f'hold: stay unless timer > {best[2]} and not acceptable(h={best[0]}, z={best[1]})')
    combat = Score('hold: COMBAT acceptable only (stay iff acceptable)')
    sub = Score('hold, own tile unacceptable: stay (rule) ')
    rates = collections.Counter()
    for r, n, tm in hold:
        sc.add(r, hold_rule(r, tm, *best), n['end_on'], True, dict(timer=tm, hpf=round(r['hpf'], 3), danger=round(r['danger0'], 3)))
        combat.add(r, acceptable(r), n['end_on'], True)
        if not acceptable(r):
            sub.add(r, hold_rule(r, tm, *best), n['end_on'], False)
        t = 'none' if tm is None else str(tm)
        rates[f"timer={t}/{'acceptable' if acceptable(r) else 'unacceptable'}", n['end_on']] += 1
    for s in (sc, combat, sub):
        print(s.line())
    res['hold'] = dict(params=dict(h=best[0], z=best[1], tmax=best[2]), rule=sc.report(), combat_only=combat.report(),
                       unacceptable_subset=sub.report(),
                       stay_rates={k: [rates[k, True], rates[k, True] + rates[k, False]]
                                   for k in sorted({k for k, _ in rates})})
    # Contested.
    con = data['contested']
    fit = [x for x in con if x[0]['cohort'] in FIT]
    grid = [(h, z) for h in [i / 20 for i in range(0, 21)] for z in (0.1, 0.2, 0.28, 0.4, 0.6, 1.0, 99)]
    best = max(grid, key=lambda g: sum(acceptable(r, *g) == n['end_on'] for r, n, _ in fit))
    sc = Score(f'contested: stay iff acceptable(h={best[0]}, z={best[1]})')
    z0 = Score('contested: stay iff COMBAT acceptable (0.49/0.28)')
    hit = collections.Counter()
    for r, n, _ in con:
        sc.add(r, acceptable(r, *best), n['end_on'], True, dict(hpf=round(r['hpf'], 3), danger=round(r['danger0'], 3)))
        z0.add(r, acceptable(r), n['end_on'], True)
        hit['rows'] += 1
        hit['hit any enemy'] += bool(r['hit_ids'])
        hit['hit an enemy on the group'] += bool(set(r['hit_ids']) & set(n['en_on']))
        hit['enemy on group within basic reach'] += any(e['id'] in n['en_on'] and e['mine'] > 0 for e in r['enemies'])
    print(sc.line()); print(z0.line())
    res['contested'] = dict(params=dict(h=best[0], z=best[1]), rule=sc.report(), combat=z0.report(), hits=dict(hit))
    # Enemy-held groups beside Fish.
    eh = data['enemy-held']
    sc = Score('enemy-held, 1 tile away: never steps on')
    rates = collections.Counter()
    for r, n, _ in eh:
        sc.add(r, False, n['end_on'], False)
        k = ('acceptable' if acceptable(r) else 'unacceptable', 'free tile' if n['free'] else 'no free tile')
        rates[k, n['end_on']] += 1
        rates[k, 'hit'] += bool(set(r['hit_ids']) & set(n['en_on']))
    print(sc.line())
    res['enemy_held'] = dict(rule=sc.report(), rates={f'{a}/{b}': dict(stepped_on=rates[(a, b), True],
                                                                     n=rates[(a, b), True] + rates[(a, b), False],
                                                                     hit_holder=rates[(a, b), 'hit'])
                                                    for a, b in sorted({k for k, _ in rates})})
    write(out, res)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    main(p.parse_args().out)
