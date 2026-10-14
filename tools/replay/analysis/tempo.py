from collections import Counter, defaultdict

from .util import CAVEAT, cwr, fmt, mean, median, mqr, paired, paired_str, pct, wr

N_OPEN = 150
CHECKPOINTS = [50, 100, 150, 200, 300, 400, 500, 750, 1000, 1500]
LEAD_ROUNDS = [100, 200, 300, 500]


def lead_buckets(small=25, big=100):
    return [(-10**9, -big, f'<= -{big}'), (-big, -small, f'-{big - 1}..-{small}'), (-small, small, f'-{small - 1}..{small - 1}'),
            (small, big, f'{small}..{big - 1}'), (big, 10**9, f'>= {big}')]


def lead_table(sides, small, big):
    rows = []
    for lr in LEAD_ROUNDS:
        ms = [s for s in sides if f'lead_{lr}' in s]
        cells = []
        for lo, hi, lab in lead_buckets(small, big):
            b = [s for s in ms if lo <= s[f'lead_{lr}'] < hi]
            cells.append((lab, b))
        rows.append((lr, cells))
    return rows

METRICS = {
    'first_clear': ('first group cleared (round)', False, False),
    'first_capture': ('first capture paid (round)', False, False),
    'first_tribute': ('first tribute completed (round)', False, False),
    'first_tribute_gems': ('gems in the first tribute', None, False),
    'gems_per100': ('tributed gems per 100 rounds (whole game)', True, True),
    'gems_100': ('tributed gems at round 100', True, True),
    'gems_200': ('tributed gems at round 200', True, True),
    'gems_300': ('tributed gems at round 300', True, True),
    'carried_200': ('carried (untributed) gems at round 200', None, True),
    'captures_per100': ('captures per 100 rounds', True, True),
    'tributes_per100': ('tributes per 100 rounds', None, True),
    'tribute_bag': ('mean gems per tribute', None, False),
    'open_clears': (f'groups cleared in rounds 1-{N_OPEN}', True, True),
    'open_enemy_share': (f'share of rounds 1-{N_OPEN} clears on the enemy side', None, True),
    'earned_per100': ('gold earned per 100 rounds (team)', True, True),
    'bank_per_body': ('mean unspent gold per champion body', False, False),
    'spend_ratio': ('gold spent / earned', True, False),
    'first_buy': ('first shop purchase (median body, round)', False, False),
    'won': ('win rate', True, True),
    'rounds': ('game length (rounds)', None, True),
}


def _token(name):
    fam, _, rest = name.partition(' ')
    stat = name.rsplit(' ', 1)[-1]
    return f'{fam}-{ {"Strength": "Str", "Focus": "Foc", "Health": "HP"}.get(stat, stat)}'


def extract(g, P=None):
    ev, R, mp = g.events, g.rounds, g.map
    n = g.n_rounds
    sides, builds = [], []
    for t in (0, 1):
        ids = g.team_ids[t]
        idset = set(ids)
        clears = [(e['r'], mp.own_group(t, e['g'])) for e in ev if e['k'] == 'group_clear' and g.team_of.get(e.get('by')) == t]
        caps = [(e['r'], mp.own_group(t, e['g']), sum(s[1] for s in e['shares']), sum(s[2] for s in e['shares']))
                for e in ev if e['k'] == 'capture' and e['team'] == t]
        tribs = [(e['r'], e['gems'], e['a']) for e in ev if e['k'] == 'tribute_end' and e['a'] in idset]
        chs = [g.ch(c) for c in ids]
        m = {'won': int(g.winner == t), 'rounds': n}
        m['first_clear'] = clears[0][0] if clears else None
        m['first_capture'] = caps[0][0] if caps else None
        m['first_tribute'] = tribs[0][0] if tribs else None
        m['first_tribute_gems'] = tribs[0][1] if tribs else None
        m['gems_per100'] = 100 * g.final_gems[t] / n
        m['captures_per100'] = 100 * len(caps) / n
        m['tributes_per100'] = 100 * len(tribs) / n
        m['tribute_bag'] = mean([x[1] for x in tribs])
        opening = [c for c in clears if c[0] <= N_OPEN]
        m['open_clears'] = len(opening) if n >= N_OPEN else None
        m['open_enemy_share'] = (sum(1 for _, gg in opening if mp.groups[gg]['side'] == 1) / len(opening)) if opening and n >= N_OPEN else None
        m['open_route'] = [gg for _, gg in opening[:6]]
        m['open_captured'] = sorted({gg for r, gg, *_ in caps if r <= N_OPEN})
        for cp in CHECKPOINTS:
            if cp <= n:
                i = cp - 1
                m[f'gems_{cp}'] = R['gems'][t][i]
                m[f'carried_{cp}'] = sum(c['gems'][i] for c in chs if c['alive'][i])
                m[f'bank_{cp}'] = sum(c['gold'][i] for c in chs)
                m[f'earned_{cp}'] = sum(c['earned'][i] for c in chs)
        for lr in LEAD_ROUNDS:
            if lr <= n:
                m[f'lead_{lr}'] = R['gems'][t][lr - 1] - R['gems'][1 - t][lr - 1]
        earned = sum(g.champs[g.idx[c]]['earnedGold'] for c in ids)
        spent = -sum(e['gold'] for e in ev if e['k'] == 'shop' and e['a'] in idset)
        sold = sum(e['gold'] for e in ev if e['k'] == 'sell' and e['a'] in idset)
        m['earned'] = earned
        m['spent'] = spent
        m['earned_per100'] = 100 * earned / n
        m['spend_ratio'] = spent / (earned + sold) if earned + sold else None
        m['bank_per_body'] = mean([mean(c['gold']) for c in chs])
        first_buys = []
        for cid in ids:
            shops = [e for e in ev if e['k'] == 'shop' and e['a'] == cid]
            tokens, first_emblem = [], None
            for e in shops:
                if e.get('items'):
                    k = next(iter(e['items']))
                    tokens += [(e['r'], _token(k))] * max(1, round(-e['gold'] / 30))
                    if first_emblem is None and any('Emblem' in kk and v > 0 for kk, v in e['items'].items()):
                        first_emblem = e['r']
                for kk, v in (e.get('cons') or {}).items():
                    if v > 0:
                        tokens += [(e['r'], kk)] * v
            first = shops[0]['r'] if shops else None
            first_buys.append(first)
            shard_tokens = [x for x in tokens if '-' in x[1]]
            builds.append({'type': g.name_of[cid], 'team': t, 'won': int(g.winner == t), 'first_buy': first,
                           'first_emblem': first_emblem, 'seq': [x[1] for x in shard_tokens[:5]],
                           'families': Counter(x[1].split('-')[0] for x in shard_tokens),
                           'shards_300': sum(1 for x in shard_tokens if x[0] <= 300) if n >= 300 else None,
                           'cons': Counter(x[1] for x in tokens if '-' not in x[1])})
        m['first_buy'] = median(first_buys)
        sides.append(m)
    return {'sides': sides, 'builds': builds}


def _split(rows):
    return [r for r in rows if r['won']], [r for r in rows if not r['won']]


def render(ctx, rep):
    sides = ctx.side_metrics()
    maps = sorted({s['map'] for s in sides})
    rep.p(CAVEAT)
    rep.p(f'Set: {ctx.describe()}. Sides analysed: {len(sides)} ({sum(s["won"] for s in sides)} won). '
          'Own-side frame: team B positions and camp groups are mirrored onto team A\'s side, so labels mean the same place for both teams. '
          'Group labels are `<types>(x,y)<side>`: W wolf, E elk, G gem cluster, $ gold cluster, M monolith; side o = own half, e = enemy half, m = middle.')

    rep.h('Game length')
    rows = []
    for mname in maps + ['(all)']:
        gs = [gi for gi in ctx.games if mname == '(all)' or gi['map'] == mname]
        lens = [gi['rounds'] for gi in gs]
        gemwin = sum(1 for gi in gs if max(gi['gems']) >= 1000)
        rows.append([mname, len(gs), mqr(lens, 0), min(lens) if lens else None, max(lens) if lens else None, pct(gemwin / len(gs)) if gs else '-'])
    rep.table(['map', 'games', 'rounds median [p25-p75]', 'min', 'max', 'ended by 1000 gems'], rows, 'length')

    rep.h(f'Opening routes (groups cleared in rounds 1-{N_OPEN}, own frame)')
    rep.p('Route = first three groups the side cleared (killed the last monster of), in order. "share" = sides with that route on that map.')
    route_rows, group_rows = [], []
    for mname in maps:
        ms = [s for s in sides if s['map'] == mname and s['open_clears'] is not None]
        mp = ctx.map_of(mname)
        routes = Counter(tuple(s['open_route'][:3]) for s in ms)
        for route, k in routes.most_common(6):
            rs = [s for s in ms if tuple(s['open_route'][:3]) == route]
            route_rows.append([mname, ' > '.join(mp.group_label(x) for x in route) or '(none)', k, pct(k / len(ms)), cwr([(s['cluster'], s['won']) for s in rs])])
        w, l = _split(ms)
        cnt = Counter(x for s in ms for x in set(s['open_route']))
        for gg, k in cnt.most_common():
            if k < max(3 if len(ms) >= 20 else 1, len(ms) // 10):
                continue
            wk = sum(1 for s in w if gg in s['open_route'])
            lk = sum(1 for s in l if gg in s['open_route'])
            group_rows.append([mname, mp.group_label(gg), pct(k / len(ms)), pct(wk / len(w)) if w else '-', pct(lk / len(l)) if l else '-', len(w), len(l)])
    rep.table(['map', 'route', 'sides', 'share', 'win rate (n, clusters, 95% CI)'], route_rows, 'routes')
    rep.p('Which groups get cleared early, winners vs losers (only groups cleared early by at least 10% of sides):')
    rep.table(['map', 'group', 'all sides', 'winners', 'losers', 'n winners', 'n losers'], group_rows, 'opening_groups')
    oc = paired(ctx.pairs('open_clears'))
    oe = paired(ctx.pairs('open_enemy_share'))
    rep.p(f'Groups cleared in rounds 1-{N_OPEN}: winners {mqr([s["open_clears"] for s in sides if s["won"]])}, '
          f'losers {mqr([s["open_clears"] for s in sides if not s["won"]])}. Same game: {paired_str(oc)}.',
          f'Share of those clears on the enemy side: winners {mqr([s["open_enemy_share"] for s in sides if s["won"]], 2)}, '
          f'losers {mqr([s["open_enemy_share"] for s in sides if not s["won"]], 2)}. Same game: {paired_str(oe)}.')
    if oc and oc['n'] >= 20:
        rep.highlight(f'Opening clears (rounds 1-{N_OPEN}, before most outcomes are settled): {paired_str(oc)} (same-game pairs).')

    rep.h('Time to first capture and first tribute')
    rep.p('First capture = first capture payout to the side; first tribute = first tribute_end by the side. '
          '"Same game" compares the winner with the loser of each game (lower is earlier).')
    rows = []
    for mname in maps + ['(all)']:
        ms = [s for s in sides if mname == '(all)' or s['map'] == mname]
        w, l = _split(ms)
        for key in ('first_clear', 'first_capture', 'first_tribute'):
            p = paired(ctx.pairs(key, mname))
            rows.append([mname, key, mqr([s[key] for s in w], 0), mqr([s[key] for s in l], 0),
                         f'{p["lt"]}/{p["n"]} ({pct(p["lt"] / p["n"])}; {pct(p["ci_lt"][0])}-{pct(p["ci_lt"][1])}, c={p["clusters"]})' if p and p['ci_lt'][0] is not None else '-',
                         f'{fmt(p["diff"])} [{fmt(p["ci_diff"][0])}..{fmt(p["ci_diff"][1])}]' if p else '-'])
    rep.table(['map', 'metric', 'winners', 'losers', 'winner earlier (same game; cluster CI)', 'median diff [CI]'], rows, 'first_times')
    for key in ('first_capture', 'first_tribute'):
        p = paired(ctx.pairs(key))
        if p and p['n'] >= 20:
            rep.highlight(f'{key.replace("_", " ")} (early-game behaviour): {paired_str(p, lower_better=True)}; overall median {fmt(median([s[key] for s in sides]), 0)}.')

    rep.h('Gems: tribute rate, tributed vs carried over time')
    rows = []
    for mname in maps + ['(all)']:
        ms = [s for s in sides if mname == '(all)' or s['map'] == mname]
        w, l = _split(ms)
        rows.append([mname, mqr([s['gems_per100'] for s in w]), mqr([s['gems_per100'] for s in l]),
                     mqr([s['tribute_bag'] for s in w]), mqr([s['tribute_bag'] for s in l]),
                     mqr([s['tributes_per100'] for s in w]), mqr([s['tributes_per100'] for s in l])])
    rep.table(['map', 'gems/100r winners', 'gems/100r losers', 'gems per tribute W', 'gems per tribute L', 'tributes/100r W', 'tributes/100r L'], rows, 'gem_rate')
    rows = []
    for cp in CHECKPOINTS:
        ms = [s for s in sides if f'gems_{cp}' in s]
        if len(ms) < 6:
            continue
        w, l = _split(ms)
        rows.append([cp, len(w), len(l), median([s[f'gems_{cp}'] for s in w]), median([s[f'gems_{cp}'] for s in l]),
                     median([s[f'carried_{cp}'] for s in w]), median([s[f'carried_{cp}'] for s in l]),
                     pct(mean([s[f'carried_{cp}'] / max(1, s[f'carried_{cp}'] + s[f'gems_{cp}']) for s in ms]))])
    rep.p('Medians over sides still playing at that round (all maps; per-map values in the CSV). Carried = gems in alive champions\' bags.')
    rep.table(['round', 'n W', 'n L', 'tributed W', 'tributed L', 'carried W', 'carried L', 'mean carried share'], rows)
    csv_rows = []
    for mname in maps:
        for cp in CHECKPOINTS:
            ms = [s for s in sides if s['map'] == mname and f'gems_{cp}' in s]
            if not ms:
                continue
            w, l = _split(ms)
            csv_rows.append([mname, cp, len(w), len(l), median([s[f'gems_{cp}'] for s in w]), median([s[f'gems_{cp}'] for s in l]),
                             median([s[f'carried_{cp}'] for s in w]), median([s[f'carried_{cp}'] for s in l]),
                             median([s[f'bank_{cp}'] for s in w]), median([s[f'bank_{cp}'] for s in l]),
                             median([s[f'earned_{cp}'] for s in w]), median([s[f'earned_{cp}'] for s in l])])
    rep.write_csv('timeline', ['map', 'round', 'n_w', 'n_l', 'tributed_w', 'tributed_l', 'carried_w', 'carried_l', 'bank_w', 'bank_l', 'earned_w', 'earned_l'], csv_rows)

    rep.h('Win rate by tributed-gem lead')
    rep.p('Lead = own tributed gems minus the opponent\'s at the end of that round (games still running). With a focus team, rows are that team\'s sides. '
          'Each side of a game appears once per bucket it falls in, so the table is symmetric around the level bucket.')
    small, big = ctx.params['lead_small'], ctx.params['lead_big']
    rows, csv_rows = [], []
    for lr, cells in lead_table(sides, small, big):
        rows.append([lr] + [cwr([(s['cluster'], s['won']) for s in b]) for _, b in cells])
        csv_rows += [[lr, lab, len(b), sum(s['won'] for s in b)] for lab, b in cells]
    rep.table(['round'] + [b[2] for b in lead_buckets(small, big)], rows)
    rep.write_csv('lead_winrate', ['round', 'lead', 'n', 'wins'], csv_rows)
    for lr in (100, 200, 300):
        ms = [s for s in sides if f'lead_{lr}' in s and s[f'lead_{lr}'] > 0]
        if len(ms) >= 20:
            rep.highlight(f'Ahead on tributed gems at round {lr}: win rate {cwr([(s["cluster"], s["won"]) for s in ms])}.')

    rep.h('Gold: earned, spent, banked')
    rows = []
    for mname in maps + ['(all)']:
        ms = [s for s in sides if mname == '(all)' or s['map'] == mname]
        w, l = _split(ms)
        rows.append([mname, mqr([s['earned_per100'] for s in w], 0), mqr([s['earned_per100'] for s in l], 0),
                     mqr([s['spend_ratio'] for s in w], 2), mqr([s['spend_ratio'] for s in l], 2),
                     mqr([s['bank_per_body'] for s in w], 0), mqr([s['bank_per_body'] for s in l], 0)])
    rep.table(['map', 'earned/100r W', 'earned/100r L', 'spent/earned W', 'spent/earned L', 'mean banked per body W', 'mean banked per body L'], rows, 'gold')
    rows = []
    for cp in CHECKPOINTS:
        ms = [s for s in sides if f'bank_{cp}' in s]
        if len(ms) < 6:
            continue
        w, l = _split(ms)
        rows.append([cp, median([s[f'earned_{cp}'] for s in w]), median([s[f'earned_{cp}'] for s in l]),
                     median([s[f'bank_{cp}'] for s in w]), median([s[f'bank_{cp}'] for s in l])])
    rep.p('Team totals over time (medians; per-map values in `tempo-timeline.csv`):')
    rep.table(['round', 'earned W', 'earned L', 'banked W', 'banked L'], rows)

    rep.h('Item build order and timing')
    builds = ctx.side_items('builds')
    rows, csv_rows = [], []
    by_type = defaultdict(list)
    for b in builds:
        by_type[b['type']].append(b)
    for typ, bs in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
        seqs = Counter(tuple(b['seq'][:3]) for b in bs)
        top = '; '.join(f'{" ".join(s) or "(none)"} x{k} ({pct(sum(b["won"] for b in bs if tuple(b["seq"][:3]) == s) / k)} won)' for s, k in seqs.most_common(3))
        fam = Counter()
        for b in bs:
            fam.update(b['families'])
        tot = sum(fam.values()) or 1
        w, l = _split(bs)
        famw, faml = Counter(), Counter()
        for b in w:
            famw.update(b['families'])
        for b in l:
            faml.update(b['families'])
        fams = ', '.join(f'{f} {pct(k / tot)} (W {pct(famw[f] / max(1, sum(famw.values())))} / L {pct(faml[f] / max(1, sum(faml.values())))})' for f, k in fam.most_common(3))
        rows.append([typ, len(bs), mqr([b['first_buy'] for b in bs], 0), mqr([b['first_emblem'] for b in bs], 0),
                     f'{fmt(median([b["shards_300"] for b in w]))} / {fmt(median([b["shards_300"] for b in l]))}', top, fams])
        for s, k in seqs.most_common():
            csv_rows.append([typ, ' '.join(s), k, sum(b['won'] for b in bs if tuple(b['seq'][:3]) == s)])
    rep.table(['champion', 'bodies', 'first buy round', 'first emblem round', 'shards by r300 W / L', 'top first-3 shards', 'shard families (share, W / L)'], rows, 'builds')
    rep.write_csv('build_sequences', ['champion', 'first3', 'n', 'wins'], csv_rows)
    rep.p('Opening shard family (family of each body\'s first shard) by team, with the team\'s win rate for each choice. '
          'Family choice is mostly a team signature, so compare within a team before reading it as an effect:')
    by_team = defaultdict(lambda: defaultdict(list))
    for gi in ctx.games:
        for t in ctx.focus_teams(gi):
            fam = Counter(b['seq'][0].split('-')[0] for b in ctx.data[gi['dir']]['tempo']['builds'] if b['team'] == t and b['seq'])
            if fam:
                k = fam.most_common(1)[0][0]
                by_team[gi['names'][t]][k].append((gi['cluster'], int(gi['winner'] == t)))
    rows = []
    for name, fams in sorted(by_team.items(), key=lambda kv: -sum(len(v) for v in kv[1].values())):
        rows.append([name, sum(len(v) for v in fams.values()), '; '.join(f'{f} {len(v)} ({cwr(v)})' for f, v in sorted(fams.items(), key=lambda kv: -len(kv[1])))])
    rep.table(['team', 'sides', 'main opening family: sides (win rate)'], rows, 'opening_family')
    cons = Counter()
    for b in builds:
        cons.update(b['cons'])
    if cons:
        rep.p('Consumables bought: ' + ', '.join(f'{k} {v}' for k, v in cons.most_common()) + f' (over {len(builds)} bodies).')
    p = paired(ctx.pairs('spend_ratio'))
    if p and p['n'] >= 20:
        rep.p(f'Spent/earned, same game: {paired_str(p)}.')
