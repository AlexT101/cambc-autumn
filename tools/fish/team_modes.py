"""TEAM.md section 1b: a complete priority selector for Fish, from the writer's own view.

    dead                    -> L = -1
    contested camp (k)      -> late:    L = band + 5
    enemy in reach          -> contact: L = 99 + j if the enemy starts next round, else -101 - j
    otherwise               -> quiet:   L = band
priority = -rank - (N+1)*L; rank from base max health (team_priority.py); j = min(16, floor(16*T/ehp)).
contested camp (k): some visible awake monster with a range has the writer in range, and a visible
enemy is within range + k of an awake member of that monster's group. k is fitted on discovery.
The early mode (L in [-5,-1] alive) has no recovered trigger and is never predicted.

    python3 tools/fish/team_modes.py research/fish-2026-11-05/team-modes.json
"""
import collections
import gzip
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from team_common import HELD_OUT, write_json  # noqa: E402

COHORTS = ['model', 'confirm', 'third', 'fourth', 'fifth', 'sixth']
BASE_HP = [1200, 1000, 900, 600, 900, 650, 700, 1200, 700, 900, 1000, 900, 1000]


def load():
    rows, teams = [], collections.defaultdict(dict)
    for c in COHORTS:
        with gzip.open(f'replays/fish-team-rows/{c}-rows-v2.jsonl.gz', 'rt') as f:
            for line in f:
                r = json.loads(line)
                teams[r['game']][r['id']] = r['type']
                rows.append(r)
    rank = {}
    for game, t in teams.items():
        for k, i in enumerate(sorted(t, key=lambda i: (-BASE_HP[t[i]], t[i], i))):
            rank[(game, i)] = k + 2
    return rows, rank


def predict(r, k, rank, use_late=True):
    n = r['n']
    rk = rank[(r['game'], r['id'])]
    if not r['alive']:
        mode, L = 'dead', -1
    elif use_late and r[f'contest{k}']:
        mode, L = 'late', r['band'] + 5
    elif r['inreach']:
        j = min(16, math.floor(16 * r['threat_ratio']))
        mode, L = 'contact', (99 + j) if not r['fish_starts_next'] else (-101 - j)
    else:
        mode, L = 'quiet', r['band']
    return mode, -rk - (n + 1) * L


def actual_mode(r):
    if not r['alive']:
        return 'dead'
    m = r['mode']
    return 'contact' if m.startswith('contact') else m


def score(rows, rank, k, use_late=True, keep=lambda r: True):
    C = collections.Counter()
    conf = collections.Counter()
    for r in rows:
        if not keep(r):
            continue
        pm, pv = predict(r, k, rank, use_late)
        am = actual_mode(r)
        C['n'] += 1
        C['mode'] += pm == am
        C['value'] += pv == r['value']
        C['base quiet mode'] += am == ('dead' if not r['alive'] else 'quiet')
        conf[(pm, am)] += 1
        if pm in ('late', 'contact') or am in ('late', 'contact'):
            C['sign-only contact'] += (pm == am == 'contact') and ((pv > 0) == (r['value'] > 0))
    return C, conf


def main(out):
    rows, rank = load()
    written = set()
    kept = []
    for r in rows:  # skip each champion's turns before its first write (start priority 0)
        if r['wrote']:
            written.add((r['game'], r['id']))
        if (r['game'], r['id']) in written:
            kept.append(r)
    disc = [r for r in kept if r['cohort'] not in HELD_OUT]
    held = [r for r in kept if r['cohort'] in HELD_OUT]
    vis = lambda r: r['alive'] and r['n_vis'] > 0
    fit = {}
    for k in (0, 1, 2):
        C, _ = score(disc, rank, k, keep=vis)
        fit[k] = C['mode'] / C['n']
    k = max(fit, key=fit.get)
    res = {'definitions': __doc__, 'fitted_k_discovery_mode_accuracy_enemy_visible': fit, 'k': k}
    examples = collections.defaultdict(list)
    for name, data in (('discovery', disc), ('held_out', held)):
        out_s = {}
        for subset, keep in (('all turns', lambda r: True), ('alive, enemy visible', vis)):
            C, conf = score(data, rank, k, keep=keep)
            Cn, _ = score(data, rank, k, use_late=False, keep=keep)
            out_s[subset] = {'n': C['n'], 'mode_correct': C['mode'], 'value_exact': C['value'],
                             'baseline_always_quiet_mode': C['base quiet mode'], 'without_late_rule_mode': Cn['mode'],
                             'confusion_predicted_actual': {f'{a}->{b}': v for (a, b), v in conf.most_common()}}
        res[name] = out_s
        by_cohort = {}
        for c in sorted({r['cohort'] for r in data}):
            C, _ = score([r for r in data if r['cohort'] == c], rank, k, keep=vis)
            by_cohort[c] = {'n': C['n'], 'mode_correct': C['mode'], 'baseline_always_quiet_mode': C['base quiet mode']}
        res[name]['by_cohort_enemy_visible'] = by_cohort
        for r in data:
            if not vis(r):
                continue
            pm, _ = predict(r, k, rank)
            am = actual_mode(r)
            if pm != am and len(examples[f'{name} {pm}->{am}']) < 8:
                examples[f'{name} {pm}->{am}'].append([r['game'], r['round'], r['id'], r['value'], r['dself'], r[f'contest{k}']])
    res['examples'] = examples
    write_json(out, res)
    print(json.dumps({k2: v for k2, v in res.items() if k2 not in ('definitions', 'examples')}, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
