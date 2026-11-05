"""Fish dashes near enemies: landing-tile rules and the engage/escape decision.

Fit on FIT cohorts (tactic_common), scored on HELD. Rows: tactic_rows.py `dash` and `dopp`.

Definitions
- Dash classes (dash rows, nearest pre-dash enemy within 6):
  engage = an enemy champion visible before the dash is hit later that turn (Heart of Ruin: by
  the dash landing too); escape = no hit and the landing is farther from every visible enemy than
  the pre-dash nearest distance; other = the rest.
- Landing candidates: tactic_rows.Game.landings (public terrain, units visible pre-dash).
- Engage opportunity (dopp rows, off spawn, not channelling a tribute/teleport): the nearest
  enemy is out of this turn's walk-and-hit reach but inside dash reach (melee: d 3-4; ranged: d 4-5;
  Heart of Ruin: d 2-3, where only the dash's own hit reaches). Label: dashed and hit an enemy.
- Escape opportunity: dash ready, nearest enemy within 3, off spawn. Label: escape dash.
"""
import argparse
import collections
import itertools

from tactic_common import FIT, HELD, NAMES, Score, rows, write

KEYS = {
    # dt (distance to the turn's later target) falls back to the nearest enemy for escapes.
    'danger': lambda t: t['danger'], 'dt': lambda t: t['dmin'] if t['dt'] is None else t['dt'],
    '-dt': lambda t: -(t['dmin'] if t['dt'] is None else t['dt']),
    '-adj': lambda t: -t['adj'], 'home': lambda t: t['home'], '-dmin': lambda t: -t['dmin'],
    '-step': lambda t: -t['step'], 'step': lambda t: t['step'], '-bush': lambda t: -t['bush'],
    'x': lambda t: t['p'][0], 'y': lambda t: t['p'][1], '-x': lambda t: -t['p'][0], '-y': lambda t: -t['p'][1],
}
REACH = {1: 3, 2: 2, 4: 2, 9: 2, 12: 1}  # post-dash hit reach from the landing (melee walks then hits)


def dash_class(r):
    bes = r['benemies']
    if not bes or bes[0]['d'] > 6:
        return None
    if r['tgt_ids'] and r['chosen']['dt'] is not None:
        return 'engage'
    if not r['tgt_ids'] and r['chosen']['dmin'] > bes[0]['d']:
        return 'escape'
    return 'other'


def pick(cands, order):
    key = lambda t: tuple(round(KEYS[k](t), 6) for k in order)
    best = min(key(t) for t in cands)
    return [t for t in cands if key(t) == best]


def landing_sets(r, cls):
    cs = r['cands']
    if cls == 'engage':
        reach = REACH[r['type']]
        ok = [t for t in cs if t['dt'] is not None and t['dt'] <= reach]
        return ok or cs
    if cls == 'escape':
        d0 = r['benemies'][0]['d']
        return [t for t in cs if t['dmin'] > d0] or cs
    return cs


def landing_study(data):
    out = {}
    for cls in ('engage', 'escape'):
        for group, types in (('HoR', {12}), ('melee', {2, 4, 9}), ('Vesper', {1})):
            sub = [r for r in data if r['cls'] == cls and r['type'] in types]
            fit = [r for r in sub if r['cohort'] in FIT]
            res = {}
            for n in (1, 2, 3):
                for order in itertools.permutations(KEYS, n):
                    if n > 1 and order[-1] not in ('x', 'y', '-x', '-y') and n == 3:
                        continue
                    ok = 0
                    for r in fit:
                        s = pick(landing_sets(r, cls), order)
                        ok += len(s) == 1 and s[0]['p'] == r['to']
                    res[order] = ok
            best = max(res, key=res.get)
            sc = Score(f'landing {cls} {group} {"/".join(best)}')
            meaningful = Score(f'landing {cls} {group} meaningful')
            for r in sub:
                L = landing_sets(r, cls)
                s = pick(L, best)
                pred = s[0]['p'] if len(s) == 1 else None
                # Baseline: the single-key rule most often named (danger), first tile in list order on ties.
                b = pick(L, ('danger',))[0]['p']
                sc.add(r, pred, r['to'], b, dict(n_cands=len(L)))
                if len({round(t['danger'], 6) for t in L}) > 1:
                    meaningful.add(r, pred, r['to'], b)
            rnd = collections.Counter()
            for r in sub:
                rnd[r['cohort']] += 1 / max(1, len(landing_sets(r, cls)))
            print(sc.line()); print(meaningful.line())
            out[f'{cls}/{group}'] = dict(order=best, top=sorted(((v, '/'.join(k)) for k, v in res.items()), reverse=True)[:8],
                                         all=sc.report(), danger_differs=meaningful.report(),
                                         random_expected={k: round(v, 1) for k, v in rnd.items()})
    return out


def opp_context(r):
    es = r['enemies']
    if not es or r['at_home'] or r['ch'] not in (0, 1):
        return None
    d = es[0]['d']; t = r['type']
    lo, hi = {1: (4, 5), 12: (2, 3)}.get(t, (3, 4))
    if lo <= d <= hi and r['land']:
        return 'engage'
    return None


def engage_label(r):
    return r['dashed'] and bool(r['hit_ids'])


def engage_rule(r, h, z, use_kill=True):
    hits = [t for t in r['land'] if t['hit'] > 0]
    if not hits:
        return False
    if use_kill and any(t['kill'] for t in hits):
        return True
    return r['hpf'] > h and min(t['danger'] for t in hits) <= z


def escape_label(r):
    if not r['dashed'] or r['hit_ids'] or not r['end']:
        return False
    return min(max(abs(r['end'][0] - e['x']), abs(r['end'][1] - e['y'])) for e in r['enemies']) > r['enemies'][0]['d']


def escape_rule(r, h, z):
    return r['hpf'] <= h and r['danger0'] > z


def decision_study(opps):
    out = {}
    eng = [r for r in opps if opp_context(r) == 'engage']
    esc = [r for r in opps if r['enemies'] and r['enemies'][0]['d'] <= 3 and not r['at_home'] and r['ch'] in (0, 1)]
    grid_h = [i / 100 for i in range(0, 101, 3)]
    grid_z = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.28, 0.3, 0.35, 0.4, 0.5, 0.6, 0.8, 1.0, 1.5, 2, 99]
    for name, data, rule, lab in (('engage', eng, engage_rule, engage_label), ('escape', esc, escape_rule, escape_label)):
        for group, types in (('HoR', {12}), ('melee', {2, 4, 9}), ('Vesper', {1}), ('all', {1, 2, 4, 9, 12})):
            sub = [r for r in data if r['type'] in types]
            fit = [r for r in sub if r['cohort'] in FIT]
            labs = [lab(r) for r in fit]
            best = max(((sum(rule(r, h, z) == y for r, y in zip(fit, labs)), h, z) for h in grid_h for z in grid_z))
            _, h, z = best
            maj = sum(labs) * 2 > len(labs)
            sc = Score(f'{name} dash {group} h={h} z={z}')
            for r in sub:
                sc.add(r, rule(r, h, z), lab(r), maj, dict(hpf=round(r['hpf'], 3), d=r['enemies'][0]['d']))
            res = dict(h=h, z=z, majority=maj, rule=sc.report())
            if name == 'engage':
                zero = Score(f'engage dash {group} COMBAT 0.49/0.28 (no refit)')
                for r in sub:
                    zero.add(r, rule(r, 0.49, 0.28), lab(r), maj)
                print(zero.line()); res['combat_thresholds'] = zero.report()
                rate = collections.Counter()
                for r in sub:
                    k = ('kill' if any(t['kill'] for t in r['land'] if t['hit']) else 'nokill', r['hpf'] > 0.49)
                    rate[k, lab(r)] += 1
                res['rates_fit+held'] = {f'{k[0]}/{"hp>0.49" if k[1] else "hp<=0.49"}/{"dash" if y else "no"}': v
                                         for (k, y), v in sorted(rate.items())}
            print(sc.line())
            out[f'{name}/{group}'] = res
    return out


def main(out):
    dashes = []
    cls_counts = collections.Counter()
    for r in rows(['dash']):
        c = dash_class(r)
        cls_counts[NAMES[r['type']], c or 'no enemy within 6'] += 1
        if c:
            r['cls'] = c
            dashes.append(r)
    result = dict(classes={f'{a}/{b}': v for (a, b), v in sorted(cls_counts.items())})
    result['landing'] = landing_study(dashes)
    del dashes
    opps = [r for r in rows(['dopp']) if r['enemies'] and r['enemies'][0]['d'] <= 6]
    result['decision'] = decision_study(opps)
    write(out, result)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    main(p.parse_args().out)
