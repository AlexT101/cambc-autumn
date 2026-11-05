"""TEAM.md section 1: Fish's priority levels, modes and what they do to turn order.

Inputs: replays/fish-team-rows/<cohort>-rows-v1.jsonl.gz (team_rows.py) and the observer
caches (team_decode.mjs). Rules are fixed in advance or fitted on discovery cohorts only;
held-out = fifth + sixth.

    python3 tools/fish/team_priority.py research/fish-2026-11-05/team-priority.json
"""
import collections
import gzip
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from team_common import ALIVE, HELD_OUT, ID, PRIO, decode_level, entries, load_team, mode_of, starts, write_json  # noqa: E402

COHORTS = ['model', 'confirm', 'third', 'fourth', 'fifth', 'sixth']
BASE_HP = [1200, 1000, 900, 600, 900, 650, 700, 1200, 700, 900, 1000, 900, 1000]


def split(c):
    return 'held_out' if c in HELD_OUT else 'discovery'


def rows():
    for c in COHORTS:
        with gzip.open(f'replays/fish-team-rows/{c}-rows-v1.jsonl.gz', 'rt') as f:
            for line in f:
                yield json.loads(line)


def j_of(L):
    return L - 99 if L > 0 else -L - 101


def main(out):
    res = {'definitions': {
        'level': 'priority = -rank - (N+1)*L, N = Fish bodies (Cassi and Issac separate), rank in [2, N+1]',
        'rank_rule': 'rank = 2 + position when the team is sorted by (base max health descending, type index ascending)',
        'modes': 'L=-1 dead; early L in [-5,-1] alive; quiet L = band; late L = band+5; contact- L = 99+j; contact+ L = -101-j',
        'band': 'max(0, floor(4*(1 - min(1,(hp+shield)/maxhp)*(0.65 if gems>0))))',
        'unit': 'every completed Fish turn after the champion first writes a priority; value = last priority write that turn, else the priority in effect (Fish only writes on change)',
        'reach_rule': 'contact iff some visible enemy e is within reach(e) of self or a visible ally, or within reach(self) of self; reach = 3 ranged, 2 melee',
        'j_rule': 'j = min(16, floor(16 * T / ehp)), T = sum over visible enemies of one-turn damage reach D(e, dist) (combat_common), ehp = hp + shield',
    }}
    C = collections.defaultdict(collections.Counter)
    ranks = collections.defaultdict(set)
    teams = collections.defaultdict(dict)
    examples = collections.defaultdict(list)
    ally_late = collections.defaultdict(collections.Counter)
    written = set()
    for r in rows():
        s = split(r['cohort'])
        if r['wrote']:
            written.add((r['game'], r['id']))
        if (r['game'], r['id']) not in written:
            C[f'{s} before first write'][r['alive']] += 1  # start priority 0: never chosen by Fish
            continue
        ranks[(r['game'], r['id'])].add(r['rank'])
        teams[r['game']][r['id']] = r['type']
        C[f'{s} mode'][r['mode'] if r['alive'] else 'dead L=%d' % r['L']] += 1
        if not r['alive']:
            continue
        mode = r['mode']
        contact = mode.startswith('contact')
        if contact:
            ok = (mode == 'contact+') == r['fish_starts_next']
            C[f'{s} sign'][ok] += 1
            if not ok and len(examples[f'{s} sign']) < 12:
                examples[f'{s} sign'].append([r['game'], r['round'], r['id'], r['value']])
            j = j_of(r['L'])
            p = min(16, math.floor(16 * r['threat_ratio']))
            C[f'{s} j'][('exact' if p == j else 'pm1' if abs(p - j) <= 1 else 'miss')] += 1
            C[f'{s} j'][('base_j0_exact' if j == 0 else 'base_j0_miss')] += 1
        C[f'{s} reach'][(r['inreach'], contact)] += 1
        if r['inreach'] != contact and len(examples[f'{s} reach']) < 12:
            examples[f'{s} reach'].append([r['game'], r['round'], r['id'], r['value'], mode, r['dself'], r['dteam']])
        # Reach rule with the late override as a third outcome, for the error breakdown.
        if r['inreach'] and not contact:
            C[f'{s} reach errors'][f'predicted contact, actual {mode}'] += 1
        if contact and not r['inreach']:
            C[f'{s} reach errors']['missed contact, dself=%s' % ('none visible' if r['n_vis'] == 0 else min(r['dself'], 9))] += 1
        if r['n_vis']:
            ally_late[s][(r['ally_late'] > 0, mode == 'late')] += 1
            if not r['inreach'] and r['dself'] <= 7:
                C[f'{s} late given near, no reach'][(r['ally_late'] > 0, mode == 'late')] += 1
        if mode == 'early' or (r['n_vis'] and not r['inreach'] and r['dself'] == 4):
            C[f'{s} early at dself=4'][(r['dself'] == 4, mode)] += 1
    # Rank constancy and the base-health order.
    const = sum(len(v) == 1 for v in ranks.values())
    rank1 = sum(1 in v for v in ranks.values())
    order_ok = order_n = 0
    order_bad = []
    for game, t in teams.items():
        ids = sorted(t, key=lambda i: (-BASE_HP[t[i]], t[i], i))
        want = {i: k + 2 for k, i in enumerate(ids)}
        for i in t:
            order_n += 1
            got = ranks[(game, i)]
            if got == {want[i]}:
                order_ok += 1
            elif len(order_bad) < 12:
                order_bad.append([game, i, t[i], sorted(got), want[i]])
    res['rank'] = {'champions': len(ranks), 'constant_rank': const, 'residue_1_seen': rank1,
                   'base_health_order_matches': order_ok, 'of': order_n, 'mismatches': order_bad}
    for s in ('discovery', 'held_out'):
        rr = C[f'{s} reach']
        n = sum(rr.values())
        res[s] = {
            'rows_before_first_write': dict(C[f'{s} before first write']),
            'modes': dict(C[f'{s} mode']),
            'contact_sign': {'correct': C[f'{s} sign'][True], 'of': sum(C[f'{s} sign'].values()), 'errors': examples[f'{s} sign']},
            'reach_rule': {'correct': rr[(True, True)] + rr[(False, False)], 'of': n,
                           'baseline_never_contact': rr[(False, False)] + rr[(True, False)],
                           'contact_recall': [rr[(True, True)], rr[(True, True)] + rr[(False, True)]],
                           'contact_precision': [rr[(True, True)], rr[(True, True)] + rr[(True, False)]],
                           'errors_by_kind': dict(C[f'{s} reach errors'].most_common()), 'examples': examples[f'{s} reach']},
            'j_rule': {'exact': C[f'{s} j']['exact'], 'within_1': C[f'{s} j']['exact'] + C[f'{s} j']['pm1'],
                       'of': C[f'{s} j']['exact'] + C[f'{s} j']['pm1'] + C[f'{s} j']['miss'],
                       'baseline_j0_exact': C[f'{s} j']['base_j0_exact']},
            'late_contagion_enemy_visible': {f'ally_late={a} late={b}': v for (a, b), v in ally_late[s].items()},
            'late_near_no_reach': {f'ally_late={a} late={b}': v for (a, b), v in C[f'{s} late given near, no reach'].items()},
            'early_at_dself4': {f'{mode}': v for (d, mode), v in C[f'{s} early at dself=4'].items() if d},
        }
    res['double_turn'] = double_turns()
    write_json(out, res)
    print(json.dumps({k: v for k, v in res.items() if k != 'definitions'}, indent=1)[:6000])


def double_turns():
    """Back-to-back turns across a round boundary: the last actor of round r (enemy starts r)
    is the first of r+1 (Fish starts r+1). Counted for Fish champions by their mode in r and r+1."""
    C = collections.defaultdict(collections.Counter)
    ex = []
    for cohort, _, e in entries():
        g = load_team(e['sha256'][:16])
        side = g['side']
        team = {r['id']: r['team'] for r in g['roster']}
        n = sum(1 for r in g['roster'] if r['team'] == side)
        rs = [R for R in g['rounds'] if R['cp'] and R['order']]
        for R0, R1 in zip(rs, rs[1:]):
            if R1['r'] != R0['r'] + 1 or starts(side, R0['r']) or len(R0['order']) != 2 * n or len(R1['order']) != 2 * n:
                continue
            if sum(team[i] == side for i in R0['order']) != sum(team[i] != side for i in R0['order']):
                continue
            m0 = {c[ID]: mode_of(decode_level(c[PRIO], n)[1]) for c in R0['cp']['ch'] if team[c[ID]] == side and c[ALIVE]}
            m1 = {c[ID]: mode_of(decode_level(c[PRIO], n)[1]) for c in R1['cp']['ch'] if team[c[ID]] == side and c[ALIVE]}
            s = split(cohort)
            both = [c for c in m0 if m0[c] == 'contact-' and m1.get(c) == 'contact+']
            key = 'some champion contact-/contact+' if both else 'no such champion'
            b2b = R0['order'][-1] == R1['order'][0]
            C[f'{s} {key}'][b2b] += 1
            if both:
                C[f'{s} b2b champion is a contact one'][b2b and R0['order'][-1] in both] += 1
            if both and not b2b and len(ex) < 10:
                ex.append([g['game'], R0['r'], both])
    return {k: {'back_to_back': v[True], 'of': v[True] + v[False]} for k, v in C.items()} | {'contact_not_b2b_examples': ex}


if __name__ == '__main__':
    main(sys.argv[1])
