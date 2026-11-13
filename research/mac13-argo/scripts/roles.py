"""Champion roles (rounds 1-400) and the walking decomposition, from the extracted mirror (one pass).

    py research/mac13-argo/scripts/roles.py [--procs N] > research/mac13-argo/data/roles_raw.md

1. Per champion type, both teams pooled, rounds 1-400: labour mix (macro.py classes, % of alive rounds), camp damage per
   alive round, real recalls per 100 alive rounds (completed, or lasting 2+ rounds; feints excluded) and health share at
   their start, deaths, gold earned / spent by r300 and r600, mean Chebyshev distance to the team's living Prism.
2. Walk legs (runs of walk / walk_bag rounds) by the class of the round that ends them; for legs ending at a camp hit or
   a hold, walking distance from the leg's start to the chosen group against the nearest group that was up (monsters
   alive or cleared, not respawning) and unworked (no camp hit, no capture hold) at the leg's start; and rounds from a
   capture payout to the recipient's next camp hit.
"""

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path
from statistics import mean, median

ROOT = Path('/home/ubuntu/wt/mac13-argo')
ANA = ROOT / 'replays' / 'ana-mirror'
os.environ['CAMBC_ANALYSIS'] = str(ANA)
sys.path.insert(0, str(ROOT / 'tools' / 'replay'))

from analysis import Game  # noqa: E402
from analysis import macro  # noqa: E402
from analysis.data import chebyshev  # noqa: E402

R_MAX = 400
LEG_PH = [(1, 150, 'r1-150'), (151, 400, 'r151-400'), (401, 800, 'r401-800')]
PURPOSES = ['camp', 'hold', 'tribute/altar', 'spawn/recall', 'fight', 'wait_camp', 'died', 'regroup', 'other']
INF = 1 << 20


def ph_of(r):
    for lo, hi, nm in LEG_PH:
        if lo <= r <= hi:
            return nm
    return None


def work(d):
    try:
        return _work(d)
    except Exception as ex:
        import traceback
        return {'error': repr(ex), 'tb': traceback.format_exc(), 'dir': d}


def _work(d):
    g = Game(d)
    mp, n, R, ev = g.map, g.n_rounds, g.rounds, g.events
    nr = len(R['round'])
    champs = R['champions']
    name_of, team_of = g.name_of, g.team_of
    H = mp.H
    camp_group = {c['id']: c['group'] for c in mp.camps}
    is_mono = {grp['id']: 'Monolith' in grp['types'] for grp in mp.groups}
    cls = macro.classify(g)
    fields = macro.group_fields(mp)

    def ix(r):
        return max(0, min(r, nr) - 1)

    # group state per round (state at the end of round r) and worked flags
    st = {grp['id']: [1] * (n + 2) for grp in mp.groups}
    hold = {grp['id']: [2] * (n + 2) for grp in mp.groups}
    cur = {grp['id']: (1, 2) for grp in mp.groups}
    rows_ = R['groups']
    gi = 0
    for r in range(1, n + 1):
        while gi < len(rows_) and rows_[gi][0] <= r:
            row = rows_[gi]
            cur[row[1]] = (row[2], row[3])
            gi += 1
        for gid, (s, h) in cur.items():
            st[gid][r] = s
            hold[gid][r] = h
    hit_round = defaultdict(set)       # gid -> rounds with camp damage
    champ_hit = defaultdict(dict)      # cid -> {round: gid}
    campdmg = Counter()                # (cid) r<=400
    spent = defaultdict(lambda: [0.0, 0.0])   # cid -> [by r300, by r600]
    deaths = Counter()
    open_rec = {}
    recalls = defaultdict(list)        # cid -> [(start r, hp share, completed)]
    payouts = []                       # (cid, r)
    for e in ev:
        k, r = e['k'], e['r']
        if k in ('attack', 'cast') and e.get('cdmg'):
            s = 0.0
            for camp, amt in e['cdmg']:
                if amt > 0:
                    s += amt
                    gid = camp_group.get(camp)
                    if gid is not None:
                        hit_round[gid].add(r)
                        champ_hit[e['a']].setdefault(r, gid)
            if r <= R_MAX:
                campdmg[e['a']] += s
        elif k == 'shop' and (e.get('gold') or 0) < 0:
            if r <= 300:
                spent[e['a']][0] += -e['gold']
            if r <= 600:
                spent[e['a']][1] += -e['gold']
        elif k == 'death' and r <= R_MAX and e.get('linked') is None:
            deaths[e['v']] += 1
        elif k == 'recall_start':
            open_rec[e['a']] = r
        elif k in ('recall_end', 'recall_cancel'):
            r0 = open_rec.pop(e['a'], None)
            if r0 is None:
                continue
            if k == 'recall_end' or r - r0 >= 2:
                c = champs[g.idx[e['a']]]
                i = max(0, r0 - 2)
                hp, mx = c['hp'][i], c['maxHp'][i]
                recalls[e['a']].append((r0, (hp / mx) if hp is not None and mx else None, k == 'recall_end'))
        elif k == 'capture':
            for cid, gems, gold in e['shares']:
                payouts.append((cid, r))

    # ---------------- 1. roles, rounds 1..400
    out_types = defaultdict(Counter)
    rec_hp = defaultdict(list)
    prism_of = {}
    for c in champs:
        if name_of[c['id']] == 'Prism':
            prism_of[c['team']] = c
    for c in champs:
        cid, t, nm = c['id'], c['team'], name_of[c['id']]
        T = out_types[nm]
        T['n'] += 1
        q = cls[cid]
        for r in range(1, min(n, R_MAX) + 1):
            k = q[r]
            if k is None:
                continue
            T['L_' + k] += 1
            if k != 'dead':
                T['alive'] += 1
        T['campdmg'] += campdmg[cid]
        T['deaths'] += deaths[cid]
        for r0, hs, done in recalls[cid]:
            if r0 <= R_MAX:
                T['rec'] += 1
                T['rec_done'] += done
                if hs is not None:
                    rec_hp[nm].append(hs)
        for x, j in ((300, 0), (600, 1)):
            if n >= x:
                T[f'n{x}'] += 1
                T[f'earned{x}'] += c['earned'][ix(x)] or 0
                T[f'spent{x}'] += spent[cid][j]
        P = prism_of.get(t)
        if P is not None and P is not c:
            for r in range(1, min(n, R_MAX) + 1):
                i = ix(r)
                if c['alive'][i] and P['alive'][i] and c['x'][i] is not None and P['x'][i] is not None:
                    T['pd_sum'] += chebyshev((c['x'][i], c['y'][i]), (P['x'][i], P['y'][i]))
                    T['pd_n'] += 1

    # ---------------- 2. walk legs
    legs = defaultdict(lambda: [0, 0])            # (phase, purpose) -> [legs, rounds]
    walk_rounds = Counter()                        # phase -> walk rounds
    choice = defaultdict(list)                     # phase -> (chosen dist, nearest idle-up dist (any, excl. chosen), nearest excl. monolith)
    for c in champs:
        cid, t = c['id'], c['team']
        q = cls[cid]
        r = 1
        while r <= min(n, 800):
            if q[r] not in macro.WALKS:
                r += 1
                continue
            a = r
            while r <= n and q[r] in macro.WALKS:
                r += 1
            b = r - 1
            end = q[r] if r <= n else None
            ph = ph_of(a)
            if ph is None:
                continue
            i0 = max(0, a - 2)
            p0 = (c['x'][i0], c['y'][i0]) if c['alive'][i0] and c['x'][i0] is not None else None
            if end == 'camp':
                pur = 'camp'
            elif end == 'hold':
                pur = 'hold'
            elif end in ('tribute', 'wait_altar'):
                pur = 'tribute/altar'
            elif end in ('spawn', 'recall', 'teleport'):
                pur = 'spawn/recall'
            elif end == 'fight':
                pur = 'fight'
            elif end == 'dead':
                pur = 'died'
            elif end == 'wait_camp':
                pur = 'wait_camp'
            else:
                pur = 'other'
                ib = max(0, b - 1)
                p1 = (c['x'][ib], c['y'][ib]) if c['alive'][ib] and c['x'][ib] is not None else None
                if p0 and p1:
                    for c2 in champs:
                        if c2['id'] == cid or c2['team'] != t:
                            continue
                        if not (c2['alive'][i0] and c2['alive'][ib]) or c2['x'][i0] is None or c2['x'][ib] is None:
                            continue
                        if chebyshev(p1, (c2['x'][ib], c2['y'][ib])) <= 3 and chebyshev(p0, (c2['x'][i0], c2['y'][i0])) > 8:
                            pur = 'regroup'
                            break
            L_ = b - a + 1
            legs[(ph, pur)][0] += 1
            legs[(ph, pur)][1] += L_
            walk_rounds[ph] += L_
            if pur in ('camp', 'hold') and p0 is not None:
                ib = ix(r)
                if pur == 'camp':
                    gid = champ_hit[cid].get(r)
                else:
                    p = (c['x'][ib], c['y'][ib])
                    gid = mp.group_tiles.get(p)
                if gid is None:
                    continue
                k0 = p0[0] * H + p0[1]
                dc = fields[gid][k0]
                ra = max(1, a - 1)
                best, best_nm = INF, INF
                for grp in mp.groups:
                    h = grp['id']
                    if h == gid:
                        continue
                    s = st[h][ra]
                    if s not in (1, 2) or ra in hit_round[h] or (s == 2 and hold[h][ra] in (0, 1)):
                        continue
                    dd = fields[h][k0]
                    if dd < best:
                        best = dd
                    if not is_mono[h] and dd < best_nm:
                        best_nm = dd
                if dc < INF:
                    choice[ph].append((dc, best if best < INF else None, best_nm if best_nm < INF else None))
            r = b + 1
            r += 1 if r <= n and q[r] not in macro.WALKS else 0

    # ---------------- payout -> next camp hit
    gaps = []
    cens = 0
    for cid, r in payouts:
        hits = champ_hit[cid]
        nxt = next((x for x in range(r + 1, n + 1) if x in hits), None)
        if nxt is None:
            cens += 1
        else:
            gaps.append(nxt - r)
    return {'types': {k: dict(v) for k, v in out_types.items()}, 'rec_hp': dict(rec_hp),
            'legs': {f'{k[0]}|{k[1]}': v for k, v in legs.items()}, 'walk_rounds': dict(walk_rounds),
            'choice': dict(choice), 'gaps': gaps, 'cens': cens}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--procs', type=int, default=24)
    a = ap.parse_args()
    idx = json.loads((ANA / 'index.json').read_text())['games']
    dirs = sorted({r['dir'] for r in idx if r['ok']})
    types = defaultdict(Counter)
    rec_hp = defaultdict(list)
    legs = defaultdict(lambda: [0, 0])
    walk_rounds = Counter()
    choice = defaultdict(list)
    gaps, cens, bad = [], 0, 0
    with Pool(a.procs) as pool:
        for o in pool.imap_unordered(work, dirs, chunksize=4):
            if 'error' in o:
                bad += 1
                print('ERR', o['dir'], o['tb'][-500:], file=sys.stderr)
                continue
            for k, v in o['types'].items():
                types[k].update(v)
            for k, v in o['rec_hp'].items():
                rec_hp[k] += v
            for k, v in o['legs'].items():
                legs[k][0] += v[0]
                legs[k][1] += v[1]
            walk_rounds.update(o['walk_rounds'])
            for k, v in o['choice'].items():
                choice[k] += v
            gaps += o['gaps']
            cens += o['cens']
    P = print
    P(f'# Roles and walking ({len(dirs) - bad} games, {bad} errors)\n')
    P('## 1. Champion roles, rounds 1-400, both teams pooled')
    LAB = ['walk', 'walk_bag', 'camp', 'hold', 'tribute', 'recall', 'fight', 'wait_camp', 'wait_altar', 'spawn', 'idle', 'lost']
    order = ['Prism', 'Vesper Vale', 'Vendetta', 'Marcella', 'Willow', 'Cassi', 'Issac', 'Ryth', 'Heart of Ruin', 'Varg', 'Stellar', 'Ren', 'Tavi']
    P('| champion | n | ' + ' | '.join(LAB) + ' | dead (% all rds) |')
    P('|' + '---|' * (len(LAB) + 3))
    for nm in order:
        T = types.get(nm)
        if not T:
            continue
        al = T['alive'] or 1
        tot = al + T['L_dead']
        P(f'| {nm} | {T["n"]} | ' + ' | '.join(f'{100 * T["L_" + k] / al:.1f}' for k in LAB) + f' | {100 * T["L_dead"] / tot:.1f} |')
    P('')
    P('| champion | camp dmg / alive rd | real recalls / 100 alive (completed) | hp share at recall start (mean / median) | deaths / 1000 alive | gold earned r300 / r600 | gold spent r300 / r600 | mean dist to own Prism |')
    P('|---|---|---|---|---|---|---|---|')
    for nm in order:
        T = types.get(nm)
        if not T:
            continue
        al = T['alive'] or 1
        hp = rec_hp.get(nm) or []
        P(f'| {nm} | {T["campdmg"] / al:.1f} | {100 * T["rec"] / al:.2f} ({100 * T["rec_done"] / al:.2f}) | '
          + (f'{mean(hp):.2f} / {median(hp):.2f}' if hp else '-') + f' | {1000 * T["deaths"] / al:.2f} | '
          f'{T["earned300"] / max(1, T["n300"]):.0f} / {T["earned600"] / max(1, T["n600"]):.0f} | '
          f'{T["spent300"] / max(1, T["n300"]):.0f} / {T["spent600"] / max(1, T["n600"]):.0f} | '
          + (f'{T["pd_sum"] / T["pd_n"]:.1f}' if T['pd_n'] else '-') + ' |')
    P('')
    P('## 2. Walk legs by purpose (the class of the round that ends the leg)')
    P('| phase | walk rounds | ' + ' | '.join(f'{p}: % of walk rds / mean len' for p in PURPOSES) + ' |')
    P('|' + '---|' * (len(PURPOSES) + 2))
    for _, _, ph in LEG_PH:
        wr = walk_rounds[ph] or 1
        cells = []
        for p in PURPOSES:
            nl, rr = legs.get(f'{ph}|{p}', [0, 0])
            cells.append(f'{100 * rr / wr:.0f}% / {rr / nl:.1f}' if nl else '-')
        P(f'| {ph} | {walk_rounds[ph]} | ' + ' | '.join(cells) + ' |')
    P('')
    P('Legs ending at a camp hit or hold: walking steps from the leg start to the chosen group vs the nearest OTHER group up and unworked at the leg start')
    P('| phase | legs | chosen dist median / mean | nearest idle-up median | nearer idle-up group exists | one within half the chosen distance | same, excluding Monoliths | no idle-up group at all |')
    P('|---|---|---|---|---|---|---|---|')
    for _, _, ph in LEG_PH:
        v = choice.get(ph, [])
        if not v:
            continue
        dcs = [x[0] for x in v]
        nb = [x[1] for x in v if x[1] is not None]
        nearer = mean(x[1] is not None and x[1] < x[0] for x in v)
        half = mean(x[1] is not None and x[1] <= x[0] / 2 for x in v)
        half_nm = mean(x[2] is not None and x[2] <= x[0] / 2 for x in v)
        none = mean(x[1] is None for x in v)
        P(f'| {ph} | {len(v)} | {median(dcs):.0f} / {mean(dcs):.1f} | {median(nb) if nb else "-"} | {100 * nearer:.0f}% | {100 * half:.0f}% | {100 * half_nm:.0f}% | {100 * none:.0f}% |')
    # distance buckets
    allv = [x for ph in choice for x in choice[ph]]
    P('')
    for lo, hi in ((0, 5), (6, 10), (11, 20), (21, 40), (41, 10 ** 6)):
        v = [x for x in allv if lo <= x[0] <= hi]
        if v:
            P(f'- chosen {lo}-{hi if hi < 10 ** 6 else "+"} steps: {len(v)} legs, a non-Monolith idle-up group within half the distance in {100 * mean(x[2] is not None and x[2] <= x[0] / 2 for x in v):.0f}%')
    P('')
    P(f'Capture payout -> the recipient\'s next camp hit: median {median(gaps)} rounds, IQR {sorted(gaps)[len(gaps) // 4]}-{sorted(gaps)[3 * len(gaps) // 4]}, '
      f'mean {mean(gaps):.1f}; {len(gaps)} payouts with a later hit, {cens} with none (game ended or never hit again).')


if __name__ == '__main__':
    main()
