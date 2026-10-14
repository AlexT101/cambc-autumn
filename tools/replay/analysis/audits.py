from collections import Counter, defaultdict

from .data import chebyshev
from . import params as params_mod
from .util import CAVEAT, boot_ratio, by_cluster, crate, fmt, mean, median, pct, quantile

LOOKBACK = 40
SHOP_GOLD = 30
SAFE_RUN = 6

METRICS = {
    'bigbag_deaths_per1000': ('large-bag deaths per 1000 rounds', False, True),
    'camp_deaths_per1000': ('deaths to camps per 1000 rounds', False, False),
    'camp_gems_per1000': ('carried gems lost to camp deaths per 1000 rounds', False, False),
    'camp_dmg_ratio': ('camp damage taken / camp damage dealt (engine statistics)', False, False),
    'dead_share': ('champion-rounds spent dead', False, True),
    'recall_cancel_rate': ('recalls cancelled / started', False, True),
    'recall_camp_cancel_rate': ('recalls cancelled by camp damage / started', False, False),
    'tribute_cancel_rate': ('tributes cancelled / started', False, True),
    'reset_rate': ('capture resets / capture holds', False, True),
    'walkoff_rate': ('own walk-offs (not contested, not death) / holds', False, False),
    'stolen_rate': ('groups cleared but captured by the enemy / clears', False, True),
    'idle_rate': ('idle turns / alive turns (rounds 2+)', None, False),
    'idle_other_rate': ('idle turns away from camp tiles, spawn and camps / alive turns', False, False),
    'bank_share': ('alive champion-rounds holding 150+ gold', False, False),
    'unspent_shop_share': (f'rounds on own spawn or dead with {SHOP_GOLD}+ unspent gold / such rounds', False, False),
    'wasted_cast_rate': ('casts that hit nothing or failed to stun / such casts', False, False),
    'fuel_rate': ('out-of-fuel turns / alive turns (rounds 2+)', False, False),
}


def extract(g, P=None):
    P = P or params_mod.DEFAULTS
    BANK_GOLD, BANK_ROUNDS, E = P['bank_gold'], P['bank_rounds'], P['early']
    mp, ev, n = g.map, g.events, g.n_rounds
    by_step = defaultdict(list)
    for e in ev:
        by_step[e['s']].append(e)
    dmgd = g.damaged_rounds
    death_steps = {(e['s'], e['v']) for e in g.deaths}
    sides = []
    examples = []
    for t in (0, 1):
        ids = g.team_ids[t]
        idset = set(ids)
        m = {}
        bags = [e['gems'] for e in ev if e['k'] == 'tribute_start' and e['a'] in idset]
        m['tribute_bags'] = bags
        deaths = []
        for e in g.deaths:
            if e['v'] not in idset or e['gems'] <= 0:
                continue
            cid, r, bag = e['v'], e['r'], e['gems']
            ch = g.ch(cid)
            half = max(1, bag // 2)
            run = best = 0
            passed = None
            carry = 0
            for rr in range(r - 1, max(0, r - LOOKBACK) - 1, -1):
                i = rr - 1
                if i < 0 or not ch['alive'][i] or ch['gems'][i] < half:
                    break
                carry += 1
                ok = rr not in dmgd[cid] and ch['chan'][i] == 0 and ch['stun'][i] == 0
                run = run + 1 if ok else 0
                best = max(best, run)
                p = (ch['x'][i], ch['y'][i])
                if passed is None and ch['chan'][i] != 2 and rr >= r - 20:
                    locked = {(lx, ly) for lt, lx, ly, _ in g.rounds['locks'][i] if lt != t}
                    if any(chebyshev(p, a) <= 1 and a not in locked for a in mp.altars):
                        passed = rr
            deaths.append({'r': r, 'cid': cid, 'type': g.name_of[cid], 'gems': bag, 'camp': 'camp' in e,
                           'killer': g.label(e['by']) if 'by' in e else f'camp {e.get("camp")}', 'linked': 'linked' in e,
                           'altar_d': mp.altar_dist(tuple(e['at'])), 'recall_window': best, 'passed_altar': passed,
                           'carry_rounds': carry, 'seen': g.seen_recently(cid, r, 5), 'at': e['at']})
        m['bag_deaths'] = deaths
        camp_d = [e for e in g.deaths if e['v'] in idset and 'camp' in e]
        linked_lost = sum(e['gems'] for e in g.deaths if e['v'] in idset and 'linked' in e and any('camp' in x for x in by_step[e['s']] if x['k'] == 'death'))
        m['camp_deaths'] = len(camp_d)
        m['camp_gems'] = sum(e['gems'] for e in camp_d) + linked_lost
        m['camp_deaths_per1000'] = 1000 * len(camp_d) / n
        m['camp_gems_per1000'] = 1000 * m['camp_gems'] / n
        mt = sum(g.champs[g.idx[c]]['stats']['monsterDamageTaken'] for c in ids)
        md = sum(g.champs[g.idx[c]]['stats']['monsterDamageDone'] for c in ids)
        m['camp_dmg_ratio'] = mt / md if md else None
        dead = sum(1 for c in ids for a in g.ch(c)['alive'][1:] if not a)
        m['dead_share'] = dead / max(1, len(ids) * (n - 1))
        m['camp_death_list'] = [(e['r'], g.label(e['v']), e['gems'], e.get('camp'), e['hp']) for e in camp_d]

        rc = Counter()
        rs = [e for e in ev if e['k'] == 'recall_start' and e['a'] in idset]
        rcx = []
        for e in ev:
            if e['k'] == 'recall_cancel' and e['a'] in idset:
                cause = e['cause']
                if cause == 'damage':
                    cause = 'camp damage' if e['t'] == -1 else 'champion damage'
                rc[cause] += 1
                rcx.append((e['r'], g.label(e['a']), cause, e['gems'], e['left']))
        m['recall_starts'] = len(rs)
        m['recall_cancels'] = dict(rc)
        m['recall_cancel_list'] = rcx
        m['recall_gem_starts'] = sum(1 for e in rs if e['gems'] > 0)
        m['recall_cancel_rate'] = sum(rc.values()) / len(rs) if rs else None
        m['recall_camp_cancel_rate'] = rc['camp damage'] / len(rs) if rs else None
        ts = [e for e in ev if e['k'] == 'tribute_start' and e['a'] in idset]
        tc = Counter(e['cause'] for e in ev if e['k'] == 'tribute_cancel' and e['a'] in idset)
        m['tribute_starts'] = len(ts)
        m['tribute_cancels'] = dict(tc)
        m['tribute_cancel_rate'] = sum(tc.values()) / len(ts) if ts else None
        m['tribute_cancel_list'] = [(e['r'], g.label(e['a']), e['cause'], e['gems'], e['left']) for e in ev if e['k'] == 'tribute_cancel' and e['a'] in idset]
        m['tribute_blocked'] = sum(1 for e in ev if e['k'] == 'tribute_blocked' and e['a'] in idset)

        holds = sum(1 for e in ev if e['k'] == 'capture_hold' and e['team'] == t)
        rcl = Counter()
        resets = []
        for e in ev:
            if e['k'] != 'capture_reset' or e['team'] != t:
                continue
            same = by_step[e['s']]
            if e['contested']:
                cls = 'contested'
            elif any(x['k'] == 'death' and x['v'] in idset for x in same):
                cls = 'died on tile'
            elif any(x.get('a') in idset and x['k'] in ('move', 'cast', 'recall_end', 'teleport_end') for x in same):
                cls = 'walked off'
            elif any(x.get('a') is not None and x.get('a') not in idset for x in same):
                cls = 'enemy action'
            else:
                cls = 'other'
            rcl[cls] += 1
            actor = next((x.get('a') for x in same if x.get('a') in idset), None)
            resets.append((e['r'], mp.group_label(mp.own_group(t, e['g'])), cls, e['left'], g.label(actor) if actor is not None else '-',
                           mp.groups[e['g']]['gems']))
        m['holds'] = holds
        m['resets'] = dict(rcl)
        m['reset_list'] = resets
        m['reset_rate'] = sum(rcl.values()) / holds if holds else None
        m['walkoff_rate'] = rcl['walked off'] / holds if holds else None
        m['late_walkoffs'] = sum(1 for x in resets if x[2] == 'walked off' and x[3] <= 2)
        clears, stolen = 0, []
        pending = {}
        for e in ev:
            if e['k'] == 'group_clear':
                pending[e['g']] = (g.team_of.get(e.get('by')), e['r'])
                if g.team_of.get(e.get('by')) == t:
                    clears += 1
            elif e['k'] == 'capture' and e['g'] in pending:
                ct, cr = pending.pop(e['g'])
                if ct == t and e['team'] != t:
                    stolen.append((cr, e['r'], mp.group_label(mp.own_group(t, e['g'])), sum(s[1] for s in e['shares'])))
        m['clears'] = clears
        m['stolen'] = stolen
        m['stolen_rate'] = len(stolen) / clears if clears else None

        alive_turns = idle = fuel = fuel_r1 = 0
        idle_cls = Counter()
        bank_rounds = alive_rounds = 0
        bank_eps = []
        shop_rounds = unspent = 0
        early = Counter()
        for cid in ids:
            ch = g.ch(cid)
            run = 0
            for i, tv in enumerate(ch['turn']):
                ear = i + 1 <= E
                if i == 0:
                    fuel_r1 += tv == 6
                    continue
                alive = tv in (1, 2, 3, 5, 6)
                if alive:
                    alive_turns += 1
                    if tv == 6:
                        fuel += 1
                    if tv == 2:
                        idle += 1
                        j = i if ch['x'][i] is not None else i - 1
                        p = (ch['x'][j], ch['y'][j])
                        if p[0] is None:
                            idle_cls['elsewhere'] += 1
                        elif p in mp.group_tiles:
                            idle_cls['camp tile'] += 1
                        elif mp.in_spawn(t, p):
                            idle_cls['own spawn'] += 1
                        elif any(chebyshev(p, (c['x'], c['y'])) <= 3 for c in mp.camps):
                            idle_cls['near camp'] += 1
                        else:
                            idle_cls['elsewhere'] += 1
                gold = ch['gold'][i]
                if ch['alive'][i]:
                    alive_rounds += 1
                    early['alive_rounds'] += ear
                    if gold >= BANK_GOLD:
                        bank_rounds += 1
                        early['bank_rounds'] += ear
                        run += 1
                    else:
                        if run >= BANK_ROUNDS:
                            bank_eps.append((i + 2 - run, i + 1, g.label(cid)))
                        run = 0
                p = (ch['x'][i], ch['y'][i]) if ch['alive'][i] and ch['x'][i] is not None else None
                if not ch['alive'][i] or (p and mp.in_spawn(t, p)) or (g.name_of[cid] == 'Tavi' and ch['alive'][i]):
                    shop_rounds += 1
                    early['shop_rounds'] += ear
                    if gold >= SHOP_GOLD:
                        unspent += 1
                        early['unspent'] += ear
            if run >= BANK_ROUNDS:
                bank_eps.append((len(ch['turn']) + 1 - run, len(ch['turn']), g.label(cid)))
        early['deaths'] = sum(1 for e in g.deaths if e['v'] in idset and 'linked' not in e and e['r'] <= E)
        early['camp_deaths'] = sum(1 for e in camp_d if e['r'] <= E)
        early['recall_starts'] = sum(1 for e in rs if e['r'] <= E)
        early['recall_cancels'] = sum(1 for e in ev if e['k'] == 'recall_cancel' and e['a'] in idset and e['r'] <= E)
        early['holds'] = sum(1 for e in ev if e['k'] == 'capture_hold' and e['team'] == t and e['r'] <= E)
        early['walkoffs'] = sum(1 for x in resets if x[2] == 'walked off' and x[0] <= E)
        m['early'] = dict(early)
        m['lead_early'] = g.gems_at(t, E) - g.gems_at(1 - t, E) if n >= E else None
        m['alive_turns'] = alive_turns
        m['idle_rate'] = idle / alive_turns if alive_turns else None
        m['idle_cls'] = dict(idle_cls)
        m['idle_other_rate'] = idle_cls['elsewhere'] / alive_turns if alive_turns else None
        m['fuel_rate'] = fuel / alive_turns if alive_turns else None
        m['fuel_turns'] = fuel
        m['fuel_r1'] = fuel_r1
        m['bank_share'] = bank_rounds / alive_rounds if alive_rounds else None
        m['bank_eps'] = bank_eps
        m['unspent_shop_share'] = unspent / shop_rounds if shop_rounds else None

        stunned_at = {}
        casts = Counter()
        wasted = Counter()
        why = Counter()
        wx = []
        for e in ev:
            if e['k'] in ('attack', 'cast') and e.get('stun'):
                for v in e['stun']:
                    stunned_at[v] = e['r']
            if e['k'] != 'cast' or e['a'] not in idset:
                continue
            ab = e['ab']
            enemy_dmg = any(g.team_of.get(v, t) != t for v, _ in e.get('dmg', []))
            if ab == 'AoE damage':
                key = f'{g.name_of[e["a"]]} AoE'
                casts[key] += 1
                if not enemy_dmg and not e.get('cdmg'):
                    wasted[key] += 1
                    why['AoE hit nothing'] += 1
                    wx.append((e['r'], g.label(e['a']), key, 'hit nothing'))
            elif ab == 'CC' and e.get('tgt') in g.team_of:
                key = f'{g.name_of[e["a"]]} stun on champion'
                casts[key] += 1
                tgt = e['tgt']
                if not e.get('stun') and (e['s'], tgt) not in death_steps:
                    if g.name_of[tgt] == 'Marcella':
                        reason = 'Marcella (immune)'
                    elif stunned_at.get(tgt) == e['r'] or g.ch(tgt)['stun'][max(0, e['r'] - 2)]:
                        reason = 'already stunned'
                    else:
                        reason = 'unexplained'
                    wasted[key] += 1
                    why[f'stun: {reason}'] += 1
                    wx.append((e['r'], g.label(e['a']), key, f'no stun on {g.label(tgt)}: {reason}'))
            elif ab == 'Heal':
                key = 'Willow heal'
                casts[key] += 1
                if not any(a > 0 for _, a in e.get('heal', [])):
                    wasted[key] += 1
                    why['heal restored 0'] += 1
                    wx.append((e['r'], g.label(e['a']), key, 'healed 0'))
        m['wasted_why'] = dict(why)
        m['casts'] = dict(casts)
        m['wasted'] = dict(wasted)
        m['wasted_list'] = wx
        m['wasted_cast_rate'] = sum(wasted.values()) / sum(casts.values()) if casts else None
        sides.append(m)
    return {'sides': sides}


def _team_rows(entries, num, den, min_den=1):
    by = defaultdict(lambda: [0, 0, 0, [], []])
    for gi, t, m in entries:
        a, b = num(gi, t, m), den(gi, t, m)
        if a is None or b is None:
            continue
        x = by[gi['names'][t]]
        x[0] += a
        x[1] += b
        x[2] += 1
        x[3].append(gi['names'][1 - t])
        x[4].append(gi['ratings'][1 - t])
    rows = [(name, v[2], v[0], v[1], v[0] / v[1] if v[1] else None, v[3], v[4]) for name, v in by.items() if v[1] >= min_den]
    rows.sort(key=lambda r: -(r[4] or 0))
    return rows


def _rank(rep, entries, title, num, den, unit, csv_name, scale=1, focus=None, ctx=None):
    rows = _team_rows(entries, num, den)
    if not rows:
        return
    others = [e for e in entries if not focus or e[0]['names'][e[1]].lower() != focus]
    items = lambda es: [(e[0]['cluster'], num(*e), den(*e)) for e in es if num(*e) is not None and den(*e) is not None]
    win = [e for e in others if e[0]['winner'] == e[1]]
    lose = [e for e in others if e[0]['winner'] != e[1]]
    label = 'Other teams' if focus else 'Overall'
    rep.p(f'{label} {crate(items(others), scale)} {unit}; game winners {crate(items(win), scale)}, losers {crate(items(lose), scale)} '
          '(pooled rate [95% cluster-bootstrap CI] (clusters)).')
    team_wr = ctx.team_winrates if ctx else {}
    top = ctx.top_teams if ctx else set()
    f = lambda a, b: fmt(scale * a / b, 2) if b else '-'
    vs_top = defaultdict(lambda: [0, 0])
    for e in entries:
        if e[0]['names'][1 - e[1]] in top:
            a, b = num(*e), den(*e)
            if a is not None and b is not None:
                x = vs_top[e[0]['names'][e[1]]]
                x[0] += a
                x[1] += b
    all_opp = [team_wr.get(o) for r in rows for o in r[5] if team_wr.get(o) is not None]
    base = mean(all_opp)
    table = []
    for r in rows:
        owr = mean([team_wr.get(o) for o in r[5] if team_wr.get(o) is not None])
        rating = mean([x for x in r[6] if x is not None])
        flag = '!' if owr is not None and base is not None and abs(owr - base) > 0.1 else ''
        vt = vs_top.get(r[0])
        table.append([r[0] + (' *' if focus and r[0].lower() == focus else ''), r[1], fmt(r[2]), fmt(r[3]), f(r[2], r[3]),
                      fmt(rating, 0) if rating else '-', (pct(owr) + flag) if owr is not None else '-', f(*vt) if vt else '-'])
    rep.table(['team', 'games', 'count', 'base', unit, 'mean opp rating', 'opp win rate in set', 'vs top teams only'], table, csv_name)
    if focus:
        for i, r in enumerate(rows):
            if r[0].lower() == focus:
                rep.highlight(f'Audit {title}: {r[0]} {f(r[2], r[3])} {unit} ({r[1]} games), rank {i + 1} of {len(rows)} teams (1 = highest); '
                              f'other teams {crate(items(others), scale)}, their game winners {crate(items(win), scale)}.')
    return rows


def conditioned(entries, E, small):
    """Early-window behaviour (rounds 1..E) of game winners vs losers within the same tributed-gem-lead bucket at round E."""
    metrics = [
        ('deaths per 100 rounds', lambda x: (x.get('deaths', 0), E / 100)),
        ('camp deaths per 1000 rounds', lambda x: (x.get('camp_deaths', 0), E / 1000)),
        ('recall cancel rate', lambda x: (x.get('recall_cancels', 0), x.get('recall_starts', 0))),
        ('walk-offs per hold', lambda x: (x.get('walkoffs', 0), x.get('holds', 0))),
        (f'share of alive rounds with banked gold', lambda x: (x.get('bank_rounds', 0), x.get('alive_rounds', 0))),
        ('shop-eligible rounds with 30+ unspent', lambda x: (x.get('unspent', 0), x.get('shop_rounds', 0))),
    ]
    buckets = [('behind', lambda d: d <= -small), ('level', lambda d: -small < d < small), ('ahead', lambda d: d >= small)]
    rows = []
    for name, fn in metrics:
        row = [name]
        wdiff = []
        for bname, bf in buckets:
            es = [e for e in entries if e[2].get('lead_early') is not None and bf(e[2]['lead_early'])]
            w = [fn(e[2]['early']) for e in es if e[0]['winner'] == e[1]]
            l = [fn(e[2]['early']) for e in es if e[0]['winner'] != e[1]]
            rw = sum(a for a, _ in w) / sum(b for _, b in w) if sum(b for _, b in w) else None
            rl = sum(a for a, _ in l) / sum(b for _, b in l) if sum(b for _, b in l) else None
            row.append(f'{fmt(rw, 3)} / {fmt(rl, 3)} ({len(w)}/{len(l)})')
            if rw is not None and rl is not None:
                wdiff.append((rw - rl, len(w) + len(l)))
        tot = sum(n for _, n in wdiff)
        row.append(fmt(sum(d * n for d, n in wdiff) / tot, 3) if tot else '-')
        rows.append(row)
    return rows


def headlines(entries, P, focus=None):
    """Key audit numbers, for the sensitivity report."""
    bags = defaultdict(list)
    for gi, t, m in entries:
        bags[gi['names'][t]] += m['tribute_bags']
    thr = {name: max(P['bag_min'], quantile(b, P['bag_q']) or P['bag_min']) for name, b in bags.items()}
    out = {}
    others = [e for e in entries if not focus or e[0]['names'][e[1]].lower() != focus]
    for lab, es in (('winners', [e for e in others if e[0]['winner'] == e[1]]), ('losers', [e for e in others if e[0]['winner'] != e[1]]),
                    (focus or 'focus', [e for e in entries if focus and e[0]['names'][e[1]].lower() == focus])):
        if not es:
            continue
        big = [d for gi, t, m in es for d in m['bag_deaths'] if d['gems'] >= thr[gi['names'][t]] and not d['linked']]
        rounds = sum(gi['rounds'] for gi, _, _ in es)
        out[f'large-bag deaths/1000r, {lab}'] = 1000 * len(big) / max(1, rounds)
        out[f'large-bag deaths with recall/altar plausible, {lab}'] = mean([d['recall_window'] >= SAFE_RUN or bool(d['passed_altar']) for d in big])
        out[f'bank share, {lab}'] = mean([m['bank_share'] for _, _, m in es])
    return out


def render(ctx, rep):
    P = ctx.params
    entries = ctx.side_entries('audits', include_vs=True)
    focus = ctx.focus.lower() if ctx.focus else None
    ex_entries = [e for e in entries if not focus or e[0]['names'][e[1]].lower() == focus]
    fe = ctx.side_entries('audits')
    rep.p(CAVEAT)
    rep.p(f'Set: {ctx.describe()}' + (' (rankings also include the --vs set; * marks the focus team)' if ctx.vs_games else '') + '.',
          'Every item is "suspicious", not necessarily wrong: each table ranks teams by the rate, and examples cite `<game dir> r<round>` for checking in a replay. '
          'Rates pool counts over a team\'s games (count / base). Small bases are noisy.')

    rep.p('Ranking columns: mean opponent ladder rating (ratingBefore), the opponents\' mean win rate within this set (`!` = differs from the average '
          'opponent by more than 10 points, so the opponent mix may drive the rate), and the same rate restricted to games against the top teams '
          f'({", ".join(sorted(ctx.top_teams))}), a common set of opponents for most teams.')

    rep.h('Early-window behaviour, conditioned on the game state')
    E, small = P['early'], P['lead_small']
    cond_entries = [e for e in entries if not focus or e[0]['names'][e[1]].lower() != focus]
    rep.p(f'To reduce reverse causality: behaviour in rounds 1-{E} only, comparing game winners with losers that had the same tributed-gem lead at round {E} '
          f'(behind <= -{small}, level, ahead >= {small}). Cells: winners / losers rate (n winners / n losers). Last column: winners minus losers, '
          'weighted by bucket size.' + (' Focus team excluded.' if focus else ''))
    rep.table(['rounds 1-%d metric' % E, 'behind', 'level', 'ahead', 'weighted W - L'], conditioned(cond_entries, E, small), 'conditioned')

    rep.h('Death while carrying a large bag')
    bags = defaultdict(list)
    for gi, t, m in entries:
        bags[gi['names'][t]] += m['tribute_bags']
    P = ctx.params
    thr = {name: max(P['bag_min'], quantile(b, P['bag_q']) or P['bag_min']) for name, b in bags.items()}
    rep.p(f'Large = at least max({P["bag_min"]}, the team\'s {100 * P["bag_q"]:.0f}th-percentile tribute bag over its games). Recall plausible = in the '
          f'{LOOKBACK} rounds before death, the champion had {SAFE_RUN}+ consecutive rounds carrying at least half that bag without taking damage, channelling or being stunned '
          '(a recall needs 5 undamaged turn ends). Passed altar = it ended a round within 1 of an altar not locked by the enemy, with that bag and not channelling a tribute, in the last 20 rounds.')
    rep.p('Team thresholds: ' + ', '.join(f'{k} {v:.0f}' for k, v in sorted(thr.items())))
    big = lambda gi, t, m: [d for d in m['bag_deaths'] if d['gems'] >= thr[gi['names'][t]] and not d['linked']]
    _rank(rep, entries, 'big bag', lambda gi, t, m: len(big(gi, t, m)), lambda gi, t, m: gi['rounds'], 'per 1000 rounds', 'bigbag', 1000, focus=focus, ctx=ctx)
    rows = _team_rows(entries, lambda gi, t, m: sum(1 for d in big(gi, t, m) if d['recall_window'] >= SAFE_RUN or d['passed_altar']),
                      lambda gi, t, m: len(big(gi, t, m)))
    rep.p('Share of those deaths where a recall or tribute was plausible:')
    rep.table(['team', 'games', 'plausible', 'large-bag deaths', 'share'], [[r[0], r[1], r[2], r[3], pct(r[4])] for r in rows])
    exs = sorted(((gi, t, d) for gi, t, m in ex_entries for d in big(gi, t, m)), key=lambda x: -x[2]['gems'])
    rep.p('Examples (largest bags):')
    rep.table(['game', 'team', 'champion', 'gems', 'killed by', 'altar dist', 'recall window', 'passed altar r', 'carried for', 'enemy seen'],
              [[gi['dir'] + f' r{d["r"]}', gi['names'][t], f'{d["type"]}#{d["cid"]}', d['gems'], d['killer'], d['altar_d'], d['recall_window'], d['passed_altar'] or '-',
                d['carry_rounds'], d['seen']] for gi, t, d in exs], 'bigbag_examples', limit=15)

    rep.h('Gems lost to camp deaths')
    rep.p('A champion killed by a camp loses its whole bag (no one gains it). Includes the Cassi/Issac partner\'s bag when the camp kills one of them.')
    _rank(rep, entries, 'camp deaths', lambda gi, t, m: m['camp_deaths'], lambda gi, t, m: gi['rounds'], 'camp deaths per 1000 rounds', 'camp_deaths', 1000, focus=focus, ctx=ctx)
    _rank(rep, entries, 'camp gems', lambda gi, t, m: m['camp_gems'], lambda gi, t, m: gi['rounds'], 'gems lost per 1000 rounds', 'camp_gems', 1000, focus=focus, ctx=ctx)
    exs = sorted(((gi, t, x) for gi, t, m in ex_entries for x in m['camp_death_list']), key=lambda x: -x[2][2])
    rep.table(['game', 'team', 'champion', 'gems lost', 'camp', 'hp before'], [[gi['dir'] + f' r{x[0]}', gi['names'][t], x[1], x[2], x[3], fmt(x[4])] for gi, t, x in exs],
              'camp_death_examples', limit=12)

    rep.p('Camp damage taken per camp damage dealt (engine statistics; lower = cleaner camping, e.g. kiting, Jungle emblems, stuns on camps):')
    _rank(rep, entries, 'camp ratio', lambda gi, t, m: m['camp_dmg_ratio'], lambda gi, t, m: 1 if m['camp_dmg_ratio'] is not None else None,
          'mean camp damage taken / dealt (per game)', 'camp_dmg_ratio', focus=focus, ctx=ctx)
    rep.p('Share of champion-rounds spent dead (any cause):')
    _rank(rep, entries, 'dead', lambda gi, t, m: m['dead_share'], lambda gi, t, m: 1, 'mean dead share (per game)', 'dead_share', focus=focus, ctx=ctx)

    rep.h('Recalls and tributes cancelled')
    causes = Counter()
    for gi, t, m in entries:
        causes.update(m['recall_cancels'])
    starts = sum(m['recall_starts'] for _, _, m in entries)
    rep.p(f'Recall cancels by cause: ' + ', '.join(f'{k} {v} ({pct(v / max(1, starts))} of {starts} starts)' for k, v in causes.most_common()) +
          '. "camp damage" = cancelled in the camp phase; "champion damage" = during champion turns.')
    _rank(rep, entries, 'recall cancel', lambda gi, t, m: sum(m['recall_cancels'].values()), lambda gi, t, m: m['recall_starts'], 'cancelled / started', 'recall_cancels', focus=focus, ctx=ctx)
    rep.p('By camp damage only:')
    _rank(rep, entries, 'recall camp', lambda gi, t, m: m['recall_cancels'].get('camp damage', 0), lambda gi, t, m: m['recall_starts'], 'camp-cancelled / started', 'recall_camp', focus=focus, ctx=ctx)
    exs = sorted(((gi, t, x) for gi, t, m in ex_entries for x in m['recall_cancel_list'] if x[3] > 0), key=lambda x: -x[2][3])
    rep.table(['game', 'team', 'champion', 'cause', 'gems', 'turns left'], [[gi['dir'] + f' r{x[0]}', gi['names'][t], x[1], x[2], x[3], x[4]] for gi, t, x in exs],
              'recall_cancel_examples', limit=10)
    tcauses = Counter()
    for gi, t, m in entries:
        tcauses.update(m['tribute_cancels'])
    tstarts = sum(m['tribute_starts'] for _, _, m in entries)
    rep.p(f'Tribute cancels by cause: ' + ', '.join(f'{k} {v}' for k, v in tcauses.most_common()) + f' (of {tstarts} starts). '
          f'Tribute attempts at enemy-locked altars: {sum(m["tribute_blocked"] for _, _, m in entries)}.')
    _rank(rep, entries, 'tribute cancel', lambda gi, t, m: sum(m['tribute_cancels'].values()), lambda gi, t, m: m['tribute_starts'], 'cancelled / started', 'tribute_cancels', focus=focus, ctx=ctx)
    exs = sorted(((gi, t, x) for gi, t, m in ex_entries for x in m['tribute_cancel_list']), key=lambda x: -x[2][3])
    rep.table(['game', 'team', 'champion', 'cause', 'gems', 'turns left'], [[gi['dir'] + f' r{x[0]}', gi['names'][t], x[1], x[2], x[3], x[4]] for gi, t, x in exs], limit=8)

    rep.h('Capture resets and lost contests')
    rc = Counter()
    for gi, t, m in entries:
        rc.update(m['resets'])
    holds = sum(m['holds'] for _, _, m in entries)
    rep.p('A reset is progress lost on a held, empty group (tiles became empty or contested). Classified from the same engine step: contested, a holder died, '
          'a holder moved/dashed/recalled/teleported off ("walked off"), or an enemy action. "late" = walked off with 1-2 rounds left. '
          f'Totals: {holds} holds, ' + ', '.join(f'{k} {v}' for k, v in rc.most_common()) + '.')
    _rank(rep, entries, 'walk off', lambda gi, t, m: m['resets'].get('walked off', 0), lambda gi, t, m: m['holds'], 'walk-offs / holds', 'walkoffs', focus=focus, ctx=ctx)
    rep.p('Groups the side cleared but the enemy captured (stolen):')
    _rank(rep, entries, 'stolen', lambda gi, t, m: len(m['stolen']), lambda gi, t, m: m['clears'], 'stolen / cleared', 'stolen', focus=focus, ctx=ctx)
    exs = [(gi, t, x) for gi, t, m in ex_entries for x in m['reset_list'] if x[2] == 'walked off' and x[3] <= 2]
    exs.sort(key=lambda x: (x[2][3], -x[2][5]))
    rep.p('Late walk-offs (examples):')
    rep.table(['game', 'team', 'group (own frame)', 'rounds left', 'champion', 'group gems'], [[gi['dir'] + f' r{x[0]}', gi['names'][t], x[1], x[3], x[4], x[5]] for gi, t, x in exs],
              'late_walkoffs', limit=10)
    exs = sorted(((gi, t, x) for gi, t, m in ex_entries for x in m['stolen']), key=lambda x: -x[2][3])
    rep.p('Stolen groups (examples, cleared round -> enemy capture round):')
    rep.table(['game', 'team', 'group (own frame)', 'cleared', 'captured by enemy', 'gems'], [[gi['dir'] + f' r{x[0]}', gi['names'][t], x[2], x[0], x[1], x[3]] for gi, t, x in exs],
              'stolen_examples', limit=10)

    rep.h('Idle turns')
    ic = Counter()
    for gi, t, m in entries:
        ic.update(m['idle_cls'])
    rep.p('Idle = turn status idle (alive, not channelling, nothing done), rounds 2+. Idle on a camp tile is usually holding a capture; '
          '"near camp" (within 3 of a monster spawn) is often waiting for a respawn. ' + ', '.join(f'{k} {v}' for k, v in ic.most_common()) + '.')
    _rank(rep, entries, 'idle', lambda gi, t, m: m['idle_rate'] * m['alive_turns'] if m['alive_turns'] else None, lambda gi, t, m: m['alive_turns'], 'idle / alive turns', 'idle', focus=focus, ctx=ctx)
    rep.p('Idle elsewhere (not on a camp tile, own spawn or near a camp):')
    _rank(rep, entries, 'idle other', lambda gi, t, m: m['idle_cls'].get('elsewhere', 0), lambda gi, t, m: m['alive_turns'], 'idle elsewhere / alive turns', 'idle_elsewhere', focus=focus, ctx=ctx)

    rep.h('Gold banked')
    rep.p(f'Shopping is possible on the own spawn or while dead (Tavi: anywhere for shards); nothing costs more than 30, so unspent gold on those rounds is wasted tempo. '
          f'Banked = alive champion-rounds holding {P["bank_gold"]}+ gold; episodes are {P["bank_rounds"]}+ consecutive such rounds.')
    _rank(rep, entries, 'unspent', lambda gi, t, m: m['unspent_shop_share'], lambda gi, t, m: 1 if m['unspent_shop_share'] is not None else None,
          'mean share of shop-eligible rounds ending with 30+ unspent gold (per game)', 'unspent_shop', focus=focus, ctx=ctx)
    _rank(rep, entries, 'bank', lambda gi, t, m: m['bank_share'], lambda gi, t, m: 1 if m['bank_share'] is not None else None,
          f'mean share of alive rounds with {P["bank_gold"]}+ gold (per game)', 'bank', focus=focus, ctx=ctx)
    exs = sorted(((gi, t, x) for gi, t, m in ex_entries for x in m['bank_eps']), key=lambda x: -(x[2][1] - x[2][0]))
    rep.table(['game', 'team', 'champion', 'rounds'], [[gi['dir'] + f' r{x[0]}', gi['names'][t], x[2], f'{x[0]}-{x[1]}'] for gi, t, x in exs], 'bank_examples', limit=8)

    rep.h('Casts that hit nothing')
    cc, cw = Counter(), Counter()
    for gi, t, m in entries:
        cc.update(m['casts'])
        cw.update(m['wasted'])
    why = Counter()
    for gi, t, m in entries:
        why.update(m['wasted_why'])
    rep.p('Ground AoE that damaged no enemy champion or camp; unit stuns on a champion that applied no stun and did not kill it; heals that restored nothing. '
          'Stun failures are explained by Marcella immunity or a stun already applied that round (stuns do not stack): ' + ', '.join(f'{k} {v}' for k, v in why.most_common()) + '.')
    rep.table(['cast', 'casts', 'wasted', 'share'], [[k, v, cw[k], pct(cw[k] / v, 1)] for k, v in cc.most_common()])
    _rank(rep, entries, 'wasted', lambda gi, t, m: sum(m['wasted'].values()), lambda gi, t, m: sum(m['casts'].values()), 'wasted / casts', 'wasted_casts', focus=focus, ctx=ctx)
    exs = [(gi, t, x) for gi, t, m in ex_entries for x in m['wasted_list']]
    rep.table(['game', 'team', 'champion', 'cast', 'what'], [[gi['dir'] + f' r{x[0]}', gi['names'][t], x[1], x[2], x[3]] for gi, t, x in exs[:8]])

    rep.h('Out-of-fuel turns')
    rep.p('Turn status "fuel exhausted" (the bot ran out and lost the rest of its turn). Round 1 is listed separately: start-up is charged to it.')
    _rank(rep, entries, 'fuel', lambda gi, t, m: m['fuel_turns'], lambda gi, t, m: m['alive_turns'], 'fuel-out / alive turns (r2+)', 'fuel', focus=focus, ctx=ctx)
    r1 = _team_rows(entries, lambda gi, t, m: m['fuel_r1'], lambda gi, t, m: len(gi['ids'][t]))
    rep.table(['team', 'games', 'round-1 fuel-outs', 'bodies', 'share'], [[r[0], r[1], r[2], r[3], pct(r[4])] for r in r1 if r[2]])

    wl = lambda key: (mean([m[key] for gi, t, m in fe if gi['winner'] == t]), mean([m[key] for gi, t, m in fe if gi['winner'] != t]))
    for key, label in (('recall_cancel_rate', 'recall cancel rate'), ('walkoff_rate', 'capture walk-off rate'), ('camp_deaths_per1000', 'camp deaths per 1000 rounds'),
                       ('unspent_shop_share', 'shop-eligible rounds with 30+ unspent gold')):
        w, l = wl(key)
        if w is not None and l is not None and len(fe) >= 40:
            rep.highlight(f'Audit {label}: game winners {fmt(w, 3)} vs losers {fmt(l, 3)} (mean per side, {len(fe)} sides).')
