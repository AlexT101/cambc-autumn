"""s1: tables of priced vs realised farm choices from fc_outcomes.py's choices.jsonl.

    python research/mac13-kronos/s1/report.py [choices.jsonl] > tables.md

Units: worth in gems (gold at the choice's per_gold, as the farm prices it), rounds in rounds, per
team-game (tg) = divided by the games traced (one traced side a game).
priced = the FC line's numbers at the choice; real = from the replay (payout, switch, death).
raw priced worth = part x (group gems + per_gold x group gold): the farm's numerator without its
weights (home side, exposure, stickiness, plan) and Prism carry bonus.
"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[3] / 'replays' / 'mac13-kronos-s1-choices.jsonl.gz')
import gzip
rows = [json.loads(l) for l in (gzip.open(path, "rt") if path.endswith(".gz") else open(path))]
games = {r['game'] for r in rows}
TG = len(games)

PRICED = set('SKCJTGLQ')
for r in rows:
    r['real_rounds'] = r['end'] - r['r0']
    r['ours'] = r['outcome'] == 'ours'
    r['real_raw'] = r['share_gems'] + r['fc_pg'] * r['share_gold']
    # The team's payout of the group (in the choice or within a hold after it), at our priced part.
    team_paid = r['post_team'] == 0
    r['team_raw'] = (max(0, r['fc_p']) * (r['post_gems'] + r['fc_pg'] * r['post_gold'])) if team_paid else 0.0
    r['team_raw'] = max(r['team_raw'], r['real_raw'])
    r['pred_raw'] = r['fc_p'] * (r['g_gems'] + r['fc_pg'] * r['g_gold']) if r['fc_p'] >= 0 else None
    r['pred_gems'] = r['fc_p'] * r['g_gems'] if r['fc_p'] >= 0 else 0.0
    r['team_gems'] = max(r['share_gems'], max(0, r['fc_p']) * r['post_gems'] if r['post_team'] == 0 else 0.0)
    r['priced'] = r['fc_mode'] in PRICED and r['fc_R'] > 0
    r['pred_pay'] = r['fc_R'] - r['fc_bk'] - r['fc_H'] if r['priced'] else None  # rounds to payout, no bank detour or heal trips
    r['mclass'] = {'S': 'solo', 'K': 'solo-kite', 'C': 'crew-propose', 'J': 'crew-join'}.get(r['fc_mode'], 'other-' + r['fc_mode'])
    s = r['fc_steps']
    r['dist'] = '0-5' if s <= 5 else '6-10' if s <= 10 else '11-20' if s <= 20 else '21-35' if s <= 35 else '36+'
    r['sideL'] = {0: 'own', 1: 'enemy', -1: 'mid'}[r['side']]
    sf = r['side_frac']
    r['side5'] = 'a <.35' if sf < 0.35 else 'b .35-.45' if sf < 0.45 else 'c .45-.55' if sf < 0.55 else 'd .55-.65' if sf < 0.65 else 'e >.65'
    r0 = r['r0']
    r['phase'] = '1-100' if r0 <= 100 else '101-300' if r0 <= 300 else '301-600' if r0 <= 600 else '601-1000' if r0 <= 1000 else '1001+'
    r['prism'] = 'Prism' if r['ctype'] == 'Prism' else 'other'
    r['state'] = {0: 'alive', 1: 'cleared', 2: 'respawning'}[r['fc_st']]
    r['bank'] = 'banking' if r['fc_banking'] else 'carrying' if r['fc_bk'] != 0 else 'empty'


def med(xs):
    return st.median(xs) if xs else float('nan')


def mean(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def table(key, title, sub=None, min_n=0.2):
    sub = [r for r in rows if r['priced']] if sub is None else sub
    by = defaultdict(list)
    for r in sub:
        by[r[key]].append(r)
    out = [f'### {title}', '',
           '| ' + key + ' | choices/tg | ours % | ally % | enemy % | switched % | died % | priced R (med) | real rounds ours (med) | real/priced R ours (med) | priced gems ours | real gems ours | gem rate priced | gem rate real | real/priced | team-attr real/priced | value-unit real/priced | rounds sunk/tg | gems got/tg |',
           '|---|' + '---|' * 18]
    for k in sorted(by, key=lambda k: (str(type(k)), k)):
        g = by[k]
        n = len(g)
        if n / TG < min_n and n < 200:
            continue
        ours = [r for r in g if r['ours']]
        pct = lambda o: 100 * sum(r['outcome'] == o for r in g) / n
        pR = [r['fc_R'] for r in g]
        ratio = [r['real_rounds'] / r['pred_pay'] for r in ours if r['pred_pay'] and r['pred_pay'] > 0]
        praw = [r['pred_gems'] for r in ours]
        pay = sum(max(1, r['pred_pay']) for r in g)
        real = sum(max(1, r['real_rounds']) for r in g)
        gp = sum(r['pred_gems'] for r in g) / pay
        gr = sum(r['share_gems'] for r in g) / real
        gt = sum(r['team_gems'] for r in g) / real
        # Rates over every choice: what the choice yields a round of champion time.
        prate = sum(r['pred_raw'] or 0 for r in g) / max(1e-9, sum(max(1, r['pred_pay']) for r in g))
        rrate = sum(r['real_raw'] for r in g) / max(1e-9, sum(max(1, r['real_rounds']) for r in g))
        trate = sum(r['team_raw'] for r in g) / max(1e-9, sum(max(1, r['real_rounds']) for r in g))
        sunk = sum(r['real_rounds'] for r in g if not r['ours']) / TG
        got = sum(r['share_gems'] for r in g) / TG
        out.append(f'| {k} | {n / TG:.1f} | {pct("ours"):.0f} | {pct("ally"):.0f} | {pct("enemy"):.0f} | {pct("switched"):.0f} | {pct("died"):.0f} '
                   f'| {med(pR):.0f} | {med([r["real_rounds"] for r in ours]):.0f} | {med(ratio):.2f} | {mean(praw):.1f} | {mean([r["share_gems"] for r in ours]):.1f} '
                   f'| {gp:.3f} | {gr:.3f} | {gr / gp if gp else float("nan"):.2f} | {gt / gp if gp else float("nan"):.2f} | {rrate / prate if prate else float("nan"):.2f} | {sunk:.0f} | {got:.1f} |')
    out.append('')
    return '\n'.join(out)


def parts(key, title):
    """Priced walk / clear / hold against the replay's, on choices we were paid for."""
    by = defaultdict(list)
    for r in rows:
        if r['priced'] and r['ours'] and r['arrive'] is not None:
            by[r[key]].append(r)
    out = [f'### {title}', '', f'| {key} | n/tg | walk priced | walk real | clear priced | clear real | hold priced | hold real | total priced (no bank) | total real |',
           '|---|' + '---|' * 9]
    for k in sorted(by):
        g = by[k]
        if len(g) / TG < 0.2 and len(g) < 200:
            continue
        wp = [r['fc_t'] - r['fc_bk'] for r in g]
        wr = [r['arrive'] - r['r0'] for r in g]
        cp = [r['fc_c'] for r in g]
        cr = [(r['clear_r'] - r['arrive']) if r['clear_r'] is not None else 0 for r in g]
        hp = [r['fc_k'] for r in g]
        hr = [r['end'] - max(r['arrive'], r['clear_r'] or 0) for r in g]
        tp = [r['pred_pay'] for r in g]
        tr = [r['real_rounds'] for r in g]
        out.append(f'| {k} | {len(g) / TG:.1f} | {mean(wp):.1f} | {mean(wr):.1f} | {mean(cp):.1f} | {mean(cr):.1f} | {mean(hp):.1f} | {mean(hr):.1f} | {mean(tp):.1f} | {mean(tr):.1f} |')
    out.append('')
    return '\n'.join(out)


def ledger():
    """Champion time by outcome (all choices, priced or not)."""
    by = defaultdict(list)
    for r in rows:
        by[r['outcome']].append(r)
    total = sum(r['real_rounds'] for r in rows)
    out = ['### Champion time by outcome (all choices)', '', '| outcome | choices/tg | rounds/tg | % of choice time | median rounds | share gems/tg |', '|---|---|---|---|---|---|']
    for k in ['ours', 'ally', 'enemy', 'switched', 'died', 'gameend']:
        g = by.get(k, [])
        if not g:
            continue
        rr = sum(r['real_rounds'] for r in g)
        out.append(f'| {k} | {len(g) / TG:.1f} | {rr / TG:.0f} | {100 * rr / total:.0f} | {med([r["real_rounds"] for r in g]):.0f} | {sum(r["share_gems"] for r in g) / TG:.1f} |')
    out.append('')
    return '\n'.join(out)


def switched_detail():
    """Abandoned choices: where in the cycle they were given up, and what they switched to."""
    sw = [r for r in rows if r['outcome'] == 'switched']
    def stage(r):
        if r['arrive'] is None:
            return 'a before arrival'
        if r['fc_st'] == 2 and r['clear_r'] is None:
            return 'd at a respawning group'
        if r['fc_st'] == 0 and r['clear_r'] is None:
            return 'b clearing'
        return 'c cleared, left before payout'
    by = defaultdict(list)
    for r in sw:
        by[stage(r)].append(r)
    out = ['### Switched-away choices by stage', '', '| stage | choices/tg | rounds/tg | median rounds | priced R (med) |', '|---|---|---|---|---|']
    for k in sorted(by):
        g = by[k]
        out.append(f'| {k} | {len(g) / TG:.1f} | {sum(r["real_rounds"] for r in g) / TG:.0f} | {med([r["real_rounds"] for r in g]):.0f} | {med([r["fc_R"] for r in g if r["fc_R"] > 0]):.0f} |')
    # Cause, as far as the replay shows it: the group cleared by the enemy or paid to anyone after we left.
    def cause(r):
        if r['clear_team'] == 1:
            return 'enemy cleared it'
        if r['post_team'] == 1:
            return 'enemy captured it after'
        if r['post_team'] == 0:
            return 'team captured it after'
        if r['clear_team'] == 0:
            return 'team cleared, no payout in window'
        return 'nothing happened to it'
    byc = defaultdict(list)
    for r in sw:
        byc[cause(r)].append(r)
    out += ['', '| what became of the group | choices/tg | rounds/tg | median rounds |', '|---|---|---|---|']
    for k in sorted(byc):
        g = byc[k]
        out.append(f'| {k} | {len(g) / TG:.1f} | {sum(r["real_rounds"] for r in g) / TG:.0f} | {med([r["real_rounds"] for r in g]):.0f} |')
    # Waste: rounds of an abandoned choice not spent closing on the next choice (Chebyshev progress, so an upper bound on waste).
    pr = [r for r in sw if r['progress'] is not None]
    waste = sum(max(0, r['real_rounds'] - max(0, r['progress'])) for r in pr) / TG
    out += ['', f'Switched rounds not spent closing on the next choice (upper bound): {waste:.0f}/tg of {sum(r["real_rounds"] for r in pr) / TG:.0f}/tg.']
    # Flip-flops: A then B then A again.
    by_champ = defaultdict(list)
    for r in rows:
        by_champ[(r['game'], r['cid'])].append(r)
    flips, flip_rounds = 0, 0
    for seq in by_champ.values():
        seq.sort(key=lambda r: r['r0'])
        for x, y, z in zip(seq, seq[1:], seq[2:]):
            if x['outcome'] == 'switched' and y['outcome'] == 'switched' and z['fc_h'] == x['fc_h'] and z['r0'] - x['r0'] <= 20:
                flips += 1
                flip_rounds += x['real_rounds'] + y['real_rounds']
    out.append(f'Flip-flops (A, B, back to A within 20 rounds): {flips / TG:.1f}/tg, {flip_rounds / TG:.0f} rounds/tg.')
    short = [r for r in sw if r['real_rounds'] <= 2]
    out.append('')
    out.append(f'Switched within 2 rounds: {len(short) / TG:.1f}/tg ({100 * len(short) / max(1, len(sw)):.0f}% of switches), '
               f'{sum(r["real_rounds"] for r in short) / TG:.0f} rounds/tg.')
    out.append('')
    return '\n'.join(out)


def value_calibration():
    """Is a higher priced value a higher realised rate? Deciles of the choice's v."""
    g = sorted((r for r in rows if r['priced'] and r['fc_v'] > 0), key=lambda r: r['fc_v'])
    n = len(g)
    out = ['### Priced value deciles (priced choices)', '', '| decile | v range | n/tg | ours % | priced gem rate (part x gems / pay rounds) | real gem rate (share gems / rounds, all) | ratio |', '|---|---|---|---|---|---|---|']
    for d in range(10):
        part = g[d * n // 10:(d + 1) * n // 10]
        if not part:
            continue
        prate = sum(r['pred_gems'] for r in part) / sum(max(1, r['pred_pay']) for r in part)
        rrate = sum(r['share_gems'] for r in part) / sum(max(1, r['real_rounds']) for r in part)
        out.append(f'| {d + 1} | {part[0]["fc_v"]:.3f}-{part[-1]["fc_v"]:.3f} | {len(part) / TG:.1f} | {100 * sum(r["ours"] for r in part) / len(part):.0f} | {prate:.3f} | {rrate:.3f} | {rrate / prate:.2f} |')
    out.append('')
    return '\n'.join(out)


print(f'# s1 farm calibration: {TG} traced team-games, {len(rows)} choices ({len(rows) / TG:.1f}/tg), {sum(r["priced"] for r in rows) / TG:.1f}/tg priced\n')
print(ledger())
print(switched_detail())
print(value_calibration())
for key, title in [('mclass', 'By mode'), ('kind', 'By group type'), ('dist', 'By priced walk steps'), ('sideL', 'By map side (group nearer our spawn = own)'),
                   ('side5', 'By side fraction (dist to our spawn / sum of both)'), ('ctype', 'By champion'), ('prism', 'Prism vs others'),
                   ('phase', 'By game phase (choice round)'), ('state', 'By group state at choice'), ('bank', 'By bag (banking: the bank cycle is priced in)')]:
    print(table(key, title))
print(table('kind', 'Solo (S/K) by group type', [r for r in rows if r['priced'] and r['fc_mode'] in 'SK']))
print(table('kind', 'Crew (C/J) by group type', [r for r in rows if r['priced'] and r['fc_mode'] in 'CJ']))
for key, title in [('mclass', 'Parts by mode (paid choices)'), ('kind', 'Parts by group type (paid choices)'), ('dist', 'Parts by walk (paid choices)'),
                   ('prism', 'Parts, Prism vs others (paid choices)'), ('state', 'Parts by state at choice (paid choices)')]:
    print(parts(key, title))
