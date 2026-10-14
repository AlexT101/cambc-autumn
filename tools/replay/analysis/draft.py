from collections import Counter, defaultdict

from .util import cwr, fmt, mean, median, pct, wr

STATS = ['championDamageDone', 'championDamageTaken', 'monsterDamageDone', 'collectedGems', 'submittedGems', 'kills', 'deaths', 'assists',
         'healingDone', 'shieldingDone', 'earnedGold']


def extract(g, P=None):
    bodies = []
    for c in g.champs:
        st = c['stats']
        bodies.append({'team': c['team'], 'name': c['name'], 'won': int(g.winner == c['team']),
                       **{k: 100 * st.get(k, 0) / g.n_rounds for k in STATS}})
    return {'sides': [{'picks': list(g.picks[t]), 'comp': tuple(sorted(g.picks[t]))} for t in (0, 1)], 'bodies': bodies}


def render(ctx, rep):
    entries = ctx.side_entries('draft')
    maps = sorted({gi['map'] for gi, _, _ in entries})
    top = ctx.top_teams
    rep.p(f'Set: {ctx.describe()}. Sides: {len(entries)}. Win rates count a side as a win when that side won the game. '
          'A champion picked by both sides (mirror) always contributes one win and one loss, so the "non-mirror" column is the informative one.',
          f'Top teams (highest mean ladder rating, 20+ games): {", ".join(sorted(top))}.',
          'Draft win rates are confounded with team strength: a champion picked mainly by strong teams wins more regardless of its own value.')

    def picked(gi, t, d, champ):
        return champ in d['picks']

    rep.h('Champion pick and win rates')
    champs = Counter(c for _, _, d in entries for c in d['picks'])
    rows = []
    for c, k in champs.most_common():
        es = [(gi, t, d) for gi, t, d in entries if c in d['picks']]
        nm = [(gi, t, d) for gi, t, d in es if c not in ctx.data[gi['dir']]['draft']['sides'][1 - t]['picks']]
        first = sum(1 for _, _, d in es if d['picks'][0] == c)
        tops = [e for e in entries if e[0]['names'][e[1]] in top]
        rest = [e for e in entries if e[0]['names'][e[1]] not in top]
        rows.append([c, k, pct(k / len(entries)), wr(sum(gi['winner'] == t for gi, t, _ in es), len(es)),
                     cwr([(gi['cluster'], int(gi['winner'] == t)) for gi, t, _ in nm]), first,
                     pct(sum(1 for _, _, d in tops if c in d['picks']) / max(1, len(tops))),
                     pct(sum(1 for _, _, d in rest if c in d['picks']) / max(1, len(rest)))])
    rep.table(['champion', 'picks', 'pick rate', 'win rate', 'win rate non-mirror (n, clusters, CI)', 'first picks', 'pick rate top teams', 'pick rate others'], rows, 'champions')
    best = [r for r in rows if r[1] >= 40]
    if best:
        rep.highlight('Draft: pick rates (top teams vs others): ' + ', '.join(f'{r[0]} {r[6]} vs {r[7]}' for r in best[:6]) + '.')

    rep.h('Champion win rate per map (non-mirror)')
    rep.p('Cell = win rate (n) of sides that picked the champion when the opponent did not. Blank under 5 games.')
    rows, csv = [], []
    for c, _ in champs.most_common():
        row = [c]
        for mname in maps:
            es = [(gi, t) for gi, t, d in entries if gi['map'] == mname and c in d['picks'] and c not in ctx.data[gi['dir']]['draft']['sides'][1 - t]['picks']]
            k = sum(gi['winner'] == t for gi, t in es)
            row.append(f'{100 * k / len(es):.0f}% ({len(es)})' if len(es) >= 5 else '')
            csv.append([c, mname, len(es), k])
        rows.append(row)
    rep.table(['champion'] + maps, rows)
    rep.write_csv('champion_map', ['champion', 'map', 'n_non_mirror', 'wins'], csv)

    rep.h('Compositions')
    comps = Counter(d['comp'] for _, _, d in entries)
    rows = []
    for comp, k in comps.most_common():
        if k < 4:
            break
        es = [(gi, t, d) for gi, t, d in entries if d['comp'] == comp]
        teams = Counter(gi['names'][t] for gi, t, _ in es)
        ms = Counter(gi['map'] for gi, _, _ in es)
        rows.append([' + '.join(comp), k, cwr([(gi['cluster'], int(gi['winner'] == t)) for gi, t, _ in es]), ', '.join(f'{n} {v}' for n, v in teams.most_common(3)),
                     ', '.join(f'{n} {v}' for n, v in ms.most_common(4))])
    rep.table(['composition (sorted)', 'sides', 'win rate', 'teams', 'maps'], rows, 'compositions', limit=25)
    rep.p('Compositions are mostly team signatures, so their win rates largely measure the team, not the draft.')
    rows = []
    for mname in maps:
        ms = [(gi, t, d) for gi, t, d in entries if gi['map'] == mname]
        cs = Counter(d['comp'] for _, _, d in ms)
        for comp, k in cs.most_common(3):
            es = [(gi, t) for gi, t, d in ms if d['comp'] == comp]
            rows.append([mname, ' + '.join(comp), k, wr(sum(gi['winner'] == t for gi, t in es), k)])
    rep.table(['map', 'composition', 'sides', 'win rate'], rows, 'map_compositions')

    rep.h('Champion usage: top teams vs everyone')
    rows = []
    for name in sorted({gi['names'][t] for gi, t, _ in entries}, key=lambda n: (n not in top, n)):
        es = [d for gi, t, d in entries if gi['names'][t] == name]
        if len(es) < 5:
            continue
        cnt = Counter(c for d in es for c in d['picks'])
        rows.append([name + (' (top)' if name in top else ''), len(es), ', '.join(f'{c} {pct(k / len(es))}' for c, k in cnt.most_common(6))])
    rep.table(['team', 'sides', 'most picked (share of its games)'], rows, 'team_usage')

    rep.h('Per-champion contribution (engine end-of-game statistics, per 100 rounds)')
    rep.p('Medians (means for kills and deaths, which are mostly zero) per champion body (Cassi and Issac separately), split by whether its team won. '
          'Engine statistics are whole-game totals divided by game length.')
    bodies = ctx.side_items('bodies', 'draft')
    by = defaultdict(list)
    for b in bodies:
        by[b['name']].append(b)
    cols = ['championDamageDone', 'championDamageTaken', 'monsterDamageDone', 'collectedGems', 'submittedGems', 'kills', 'deaths', 'healingDone', 'shieldingDone']
    rows, csv = [], []
    for name, bs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        w = [b for b in bs if b['won']]
        l = [b for b in bs if not b['won']]
        agg = lambda k, xs: (mean if k in ('kills', 'deaths') else median)([b[k] for b in xs])
        rows.append([name, f'{len(w)}/{len(l)}'] + [f'{fmt(agg(k, w), 2 if k in ("kills", "deaths") else 1)} / {fmt(agg(k, l), 2 if k in ("kills", "deaths") else 1)}' for k in cols])
        for b in bs:
            csv.append([name, b['won']] + [round(b[k], 2) for k in cols])
    rep.table(['champion', 'bodies W/L'] + [f'{k}{" (mean)" if k in ("kills", "deaths") else ""} W / L' for k in cols], rows)
    rep.write_csv('bodies', ['champion', 'won'] + cols, csv)
