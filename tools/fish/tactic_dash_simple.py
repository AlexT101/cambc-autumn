"""Simple, one-key dash rules on meaningful subsets (complements tactic_dash.py's exact-tile search).

Definitions are tactic_dash.py's (classes, landing candidates, engage opportunities).
- HoR engage dash: lands where the most visible enemies are within 1 (candidates where the
  count differs).
- Engage landing: the target ends within post-dash reach (melee 2, Vesper 3, HoR 1), and among
  those tiles the danger sum is minimal (candidates where danger differs).
- Escape landing: the danger sum is minimal / the nearest enemy is farthest, over all legal
  landings (candidates where the key differs).
- Kill override: on an engage opportunity with a landing tile that kills (basic Strength from the
  landing within reach; HoR adds 1.5 x Focus within 1), Fish dashes in and hits.
"""
import argparse

from tactic_common import FIT, HELD, NAMES, Score, rows, write
from tactic_dash import REACH, dash_class, engage_label, opp_context


def close(a, b):
    return abs(a - b) < 1e-6


def main(out):
    s = {k: Score(k) for k in ('HoR engage: max enemies within 1', 'engage: target within reach of landing',
                                'engage: min danger among reaching landings', 'escape: min danger over all landings',
                                'escape: max nearest-enemy distance over all landings',
                                'escape: nearer home than the start (home distance falls)',
                                'kill from a landing: dash in and hit', 'no kill, hp > 0.49, danger <= 0.28: dash in')}
    rnd = {k: {} for k in s}  # expected hits of a uniformly random legal landing, per cohort

    rnd2 = {k: {} for k in s}  # escapes: random among landings farther than the pre-dash nearest enemy (the class's own condition)

    def chance(k, r, frac, cond=None):
        rnd[k][r['cohort']] = rnd[k].get(r['cohort'], 0) + frac
        if cond is not None:
            rnd2[k][r['cohort']] = rnd2[k].get(r['cohort'], 0) + cond

    for r in rows(['dash']):
        c = dash_class(r)
        if c is None:
            continue
        cs, ch = r['cands'], r['chosen']
        if c == 'engage':
            if r['type'] == 12 and len({t['adj'] for t in cs}) > 1:
                m = max(t['adj'] for t in cs)
                s['HoR engage: max enemies within 1'].add(r, m, ch['adj'], None)
                chance('HoR engage: max enemies within 1', r, sum(t['adj'] == m for t in cs) / len(cs))
            reach = REACH[r['type']]
            s['engage: target within reach of landing'].add(r, True, ch['dt'] <= reach)
            ok = [t for t in cs if t['dt'] is not None and t['dt'] <= reach]
            chance('engage: target within reach of landing', r, len(ok) / len(cs))
            if ch['dt'] <= reach and len({round(t['danger'], 6) for t in ok}) > 1:
                m = min(t['danger'] for t in ok)
                s['engage: min danger among reaching landings'].add(r, True, close(ch['danger'], m))
                chance('engage: min danger among reaching landings', r, sum(close(t['danger'], m) for t in ok) / len(ok))
        elif c == 'escape':
            far = [t for t in cs if t['dmin'] > r['benemies'][0]['d']]
            if len({round(t['danger'], 6) for t in cs}) > 1:
                m = min(t['danger'] for t in cs)
                s['escape: min danger over all landings'].add(r, True, close(ch['danger'], m))
                chance('escape: min danger over all landings', r, sum(close(t['danger'], m) for t in cs) / len(cs),
                       sum(close(t['danger'], m) for t in far) / len(far))
            if len({t['dmin'] for t in cs}) > 1:
                m = max(t['dmin'] for t in cs)
                s['escape: max nearest-enemy distance over all landings'].add(r, True, ch['dmin'] == m)
                chance('escape: max nearest-enemy distance over all landings', r, sum(t['dmin'] == m for t in cs) / len(cs),
                       sum(t['dmin'] == m for t in far) / len(far))
            s['escape: nearer home than the start (home distance falls)'].add(r, True, ch['home'] < r['home_d'])
            chance('escape: nearer home than the start (home distance falls)', r, sum(t['home'] < r['home_d'] for t in cs) / len(cs),
                   sum(t['home'] < r['home_d'] for t in far) / len(far))
    for r in rows(['dopp']):
        if opp_context(r) != 'engage':
            continue
        hits = [t for t in r['land'] if t['hit'] > 0]
        if any(t['kill'] for t in hits):
            s['kill from a landing: dash in and hit'].add(r, True, engage_label(r), False)
        elif hits and r['hpf'] > 0.49 and min(t['danger'] for t in hits) <= 0.28:
            s['no kill, hp > 0.49, danger <= 0.28: dash in'].add(r, True, engage_label(r), False)
    res = {}
    for k, v in s.items():
        rep = v.report()
        for part, cos in (('fit', FIT), ('held', HELD)):
            e = sum(rnd[k].get(c, 0) for c in cos)
            rep[part]['random_landing'] = round(e / rep[part]['n'], 4) if rep[part]['n'] and rnd[k] else None
            e2 = sum(rnd2[k].get(c, 0) for c in cos)
            rep[part]['random_farther_landing'] = round(e2 / rep[part]['n'], 4) if rep[part]['n'] and rnd2[k] else None
        print(v.line(), ' random landing: fit', rep['fit']['random_landing'], 'held', rep['held']['random_landing'],
              ' random farther landing: held', rep['held']['random_farther_landing'])
        res[k] = rep
    write(out, res)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    main(p.parse_args().out)
