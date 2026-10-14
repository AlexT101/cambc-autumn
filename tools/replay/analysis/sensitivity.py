from . import audits, fights, params
from .util import fmt, mean

NEEDS = {'radius': 'fights', 'gap': 'fights', 'seen_k': 'fights', 'bank_gold': 'audits', 'bank_rounds': 'audits'}


def _lead(sides, small, big):
    out = {}
    for lr in (200, 300):
        for lab, cond in (('ahead by >= small', lambda d: d >= small), ('level', lambda d: abs(d) < small), ('ahead by >= big', lambda d: d >= big)):
            out[f'win rate at r{lr}, {lab}'] = mean([s['won'] for s in sides if f'lead_{lr}' in s and cond(s[f'lead_{lr}'])])
    return out


def render(ctx, rep):
    from .cli import extract_all
    P0 = ctx.params
    gis = list({gi['dir']: gi for gi in ctx.games + ctx.vs_games}.values())
    dirs = [gi['dir'] for gi in gis]
    focus = ctx.focus.lower() if ctx.focus else None

    def entries(data):
        return [(gi, t, data[gi['dir']]['audits']['sides'][t]) for gi in gis for t in (0, 1)]

    def lead(Pv):
        sides = ctx.side_metrics() + (ctx.side_metrics(vs=True) if ctx.vs_games else [])
        return _lead(sides, Pv['lead_small'], Pv['lead_big'])

    def head(data, Pv, which):
        if which == 'fights':
            return fights.headlines(gis, data, Pv)
        if which == 'audits':
            return audits.headlines(entries(data), Pv, focus)
        return lead(Pv)

    rep.p(f'Set: every game in the sources and --vs ({len(gis)} games). Each key constant is moved to one lower and one higher value with everything else at its default; '
          'the headline numbers that depend on it are recomputed (fight and audit constants re-run the per-game extraction). '
          'A finding is robust to a constant if its direction and rough size hold across the three columns. No bootstrap here (point estimates).')
    base = {'fights': fights.headlines(gis, ctx.data, P0), 'audits': audits.headlines(entries(ctx.data), P0, focus), 'lead': lead(P0)}
    which_of = lambda k: NEEDS.get(k, 'audits' if k == 'bag_q' else 'lead')
    for key, (lo, hi) in params.SENSITIVITY.items():
        which = which_of(key)
        vals = []
        for v in (lo, hi):
            Pv = params.make(**{key: v})
            if key in NEEDS:
                data = extract_all(dirs, ctx.threads, Pv, only=[NEEDS[key]])
            else:
                data = ctx.data
            vals.append(head(data, Pv, which))
        rep.h(f'{key}: {lo} / {P0[key]} (default) / {hi}')
        rows = []
        for name, b in base[which].items():
            a, c = vals[0].get(name), vals[1].get(name)
            nums = [x for x in (a, b, c) if x is not None]
            spread = (max(nums) - min(nums)) / abs(b) if b and len(nums) == 3 else None
            sign = '' if not nums or all(x > 0 for x in nums) or all(x < 0 for x in nums) or all(x == 0 for x in nums) else 'sign flips'
            rows.append([name, fmt(a, 3), fmt(b, 3), fmt(c, 3), fmt(spread, 2), sign])
        rep.table(['headline', f'{key}={lo}', f'{key}={P0[key]}', f'{key}={hi}', 'range / default', ''], rows, key)
