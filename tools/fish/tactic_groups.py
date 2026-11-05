"""Per match group, on the HELD cohorts: does each kept rule beat its baseline in every group?

Rules (definitions in their own scripts):
- spell: max (gems + 8) / EHP vs min EHP (tactic_target.py), >= 2 candidates.
- spawn: short of full health on spawn -> stays (tactic_spawn.py); no baseline, accuracy only.
- HoR: engage dash lands with the most enemies within 1 (tactic_dash_simple.py) vs random landing.
- escape: escape dash lands at minimum danger vs a random landing farther than the nearest enemy.
- kill: a killing landing -> dash in and hit (tactic_dash_simple.py) vs never.
"""
import argparse
import collections

from tactic_common import HELD, rows, write
from tactic_dash import dash_class, engage_label, opp_context
from tactic_target import minhp, ratio
from tactic_spawn import prep


def main(out):
    g = collections.defaultdict(lambda: collections.Counter())
    for r in rows(['target'], HELD):
        if r['act'] != 'basic' and r['ability'] == 2 and len(r['cands']) >= 2:
            k = g['spell', r['group']]
            k['n'] += 1; k['ok'] += ratio(8)(r, r['cands'])['id'] == r['chosen']
            k['base'] += minhp(r, r['cands'])['id'] == r['chosen']
    for r in prep():
        if r['cohort'] in HELD and r['hpf'] < 0.999:
            k = g['spawn', r['group']]; k['n'] += 1; k['ok'] += not r['left']
    for r in rows(['spawn0'], HELD):
        if r['end'] and r['hpf'] < 0.999:
            k = g['spawn', r['group']]; k['n'] += 1; k['ok'] += not r['left']
    for r in rows(['dash'], HELD):
        c = dash_class(r); cs, ch = r['cands'], r['chosen']
        if c == 'engage' and r['type'] == 12 and len({t['adj'] for t in cs}) > 1:
            m = max(t['adj'] for t in cs); k = g['HoR', r['group']]
            k['n'] += 1; k['ok'] += ch['adj'] == m; k['base'] += sum(t['adj'] == m for t in cs) / len(cs)
        if c == 'escape' and len({round(t['danger'], 6) for t in cs}) > 1:
            m = min(t['danger'] for t in cs); far = [t for t in cs if t['dmin'] > r['benemies'][0]['d']]
            k = g['escape', r['group']]
            k['n'] += 1; k['ok'] += abs(ch['danger'] - m) < 1e-6
            k['base'] += sum(abs(t['danger'] - m) < 1e-6 for t in far) / len(far)
    for r in rows(['dopp'], HELD):
        if opp_context(r) == 'engage' and any(t['kill'] for t in r['land'] if t['hit'] > 0):
            k = g['kill', r['group']]; k['n'] += 1; k['ok'] += engage_label(r); k['base'] += not engage_label(r)
    res = collections.defaultdict(dict)
    for (rule, grp), k in sorted(g.items(), key=lambda x: (x[0][0], str(x[0][1]))):
        res[rule][str(grp)] = dict(n=k['n'], ok=k['ok'], base=round(k['base'], 1))
    summary = {}
    for rule, groups in res.items():
        beat = sum(v['ok'] > v['base'] for v in groups.values())
        tie = sum(v['ok'] == v['base'] for v in groups.values())
        summary[rule] = dict(groups=len(groups), beats_baseline=beat, ties=tie,
                             min_group_acc=min(round(v['ok'] / v['n'], 3) for v in groups.values()))
        print(rule, summary[rule])
    write(out, dict(summary=summary, groups=res))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    main(p.parse_args().out)
