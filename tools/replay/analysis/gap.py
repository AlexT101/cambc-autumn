from . import audits, economy, fights, losses, macro, tempo
from .util import fmt, mean, median, pct, quantile

ALL_METRICS = {**tempo.METRICS, **fights.METRICS, **audits.METRICS, **economy.METRICS, **macro.METRICS, **losses.METRICS}
MEAN_KEYS = set(fights.METRICS) | set(audits.METRICS) | economy.MEAN_KEYS | set(losses.METRICS)
RATE_KEYS = {k for k in ALL_METRICS if k.endswith(('rate', 'share', '_win', 'won', 'ratio', 'time', 'dmg'))} | macro.RATEISH


def _fmtm(key, v):
    if v is None:
        return '-'
    return pct(v, 1) if key in RATE_KEYS else fmt(v)


def _scale(key, xs):
    if key in MEAN_KEYS:
        m = mean(xs)
        s = (sum((x - m) ** 2 for x in xs) / max(1, len(xs) - 1)) ** 0.5
    else:
        lo, hi = quantile(xs, 0.25), quantile(xs, 0.75)
        s = (hi - lo) / 1.35
        m = median(xs)
    floor = 0.02 if key in RATE_KEYS else max(0.5, 0.05 * abs(m))
    return max(s, floor)


def render(ctx, rep):
    if not ctx.focus or not ctx.vs_games:
        rep.p('The gap report needs --team and --vs.')
        return
    focus = ctx.side_metrics()
    comp = ctx.side_metrics(vs=True)
    winners = [s for s in comp if s['won']]
    opps = sorted({s['opp'] for s in focus})
    maps = sorted({s['map'] for s in focus})
    rep.p(f'Focus: {ctx.focus} in {ctx.describe()} ({len(focus)} sides, {sum(s["won"] for s in focus)} won; opponents: {", ".join(opps)}). '
          f'Comparison: {ctx.describe(vs=True)} ({len(comp)} sides; {len(winners)} game winners).',
          'Each metric is a per-side value (one per team per game). Cells are medians (timings and economy) or means (fight and audit rates, which are mostly zero '
          'per game), over n sides. Gap z = (focus - ladder winners) / spread of all ladder sides on that map (IQR / 1.35 for medians, standard deviation for means, '
          'floored at 2 percentage points for rates). "better"/"worse" uses the metric\'s direction where one is meaningful.',
          '**Opponent caveat**: metrics marked `opp` depend heavily on the opponent. The focus games are against '
          f'{", ".join(opps)}. Against a weak opponent, kills, fight wins, gem leads, game length and anything contested should look better than they would on the ladder, '
          'and deaths should look lower, so an `opp` metric that is still worse than the ladder is a real gap (and probably larger than shown). '
          'Non-`opp` metrics (camp handling, timing to first capture/tribute, idle, fuel, banking, walk-offs) are mostly about our own play and compare fairly.')

    rows, per_map, pooled = [], [], []
    for key, (desc, better, opp) in ALL_METRICS.items():
        zs = []
        for mname in maps + ['(all)']:
            sel = lambda ss: [s.get(key) for s in ss if (mname == '(all)' or s['map'] == mname) and s.get(key) is not None]
            f, c, w = sel(focus), sel(comp), sel(winners)
            if not f or not c:
                continue
            agg = mean if key in MEAN_KEYS else median
            fm, cm, wm = agg(f), agg(c), agg(w) if w else None
            ref = wm if wm is not None else cm
            if mname == '(all)':
                z = sum(zs) / len(zs) if zs else None
            else:
                z = (fm - ref) / _scale(key, c)
                zs.append(z)
            verdict = ''
            if z is not None and better is not None and abs(z) >= 0.5:
                verdict = 'better' if (z > 0) == better else 'worse'
            rows.append([key, mname, f'{_fmtm(key, fm)} (n={len(f)})', f'{_fmtm(key, cm)} (n={len(c)})', f'{_fmtm(key, wm)} (n={len(w)})',
                         fmt(z, 2) if z is not None else '-', verdict, 'opp' if opp else ''])
            item = (abs(z) if z is not None else 0, key, mname, fm, wm, len(f), len(w), verdict, opp, desc, z)
            (pooled if mname == '(all)' else per_map).append(item)

    def line(g):
        az, key, mname, fm, wm, nf, nw, verdict, opp, desc, z = g
        where = 'all maps' if mname == '(all)' else mname
        zt = f'{z:+.1f}' if abs(z) < 10 else ('>+10' if z > 0 else '<-10')
        zs = f'mean per-map z {zt}' if mname == '(all)' else f'z {zt}'
        stat = 'mean' if key in MEAN_KEYS else 'median'
        return f'**{verdict or "n/a"}**: {desc} ({where}): {ctx.focus} {stat} {_fmtm(key, fm)} (n={nf}) vs ladder winners {_fmtm(key, wm)} (n={nw}), {zs}'

    rep.h('Largest gaps, all maps')
    rep.p('Ranked by the mean of the per-map z scores (so each map is compared against its own ladder distribution); the values shown are pooled over maps.')
    pooled.sort(key=lambda g: -g[0])
    fair = [g for g in pooled if not g[8]]
    rep.bullets([line(g) for g in fair[:15]] or ['(none)'])
    for g in [g for g in fair if g[7]][:6]:
        rep.highlight('Gap: ' + line(g).replace('**', ''))
    rep.p('Opponent-dependent metrics (read with the caveat above):')
    rep.bullets([line(g) for g in pooled if g[8]][:12] or ['(none)'])

    rep.h('Largest gaps per map')
    rep.p('Per-map focus samples are tiny (often 2 games), so treat these as pointers to replays rather than estimates.')
    per_map.sort(key=lambda g: -g[0])
    rep.bullets([line(g) for g in per_map if not g[8]][:20] or ['(none)'])

    rep.h('All metrics side by side')
    rep.table(['metric', 'map', ctx.focus, 'ladder all', 'ladder winners', 'z vs winners', 'verdict', 'opp-dependent'], rows, 'metrics')
    rep.p('Metric definitions: ' + '; '.join(f'`{k}` {v[0]}' for k, v in ALL_METRICS.items()) + '.')
