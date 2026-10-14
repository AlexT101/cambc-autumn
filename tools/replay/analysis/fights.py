import math
import random
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

from .data import chebyshev
from . import params as params_mod
from .util import CAVEAT, ascii_grid, boot_ratio, by_cluster, cwr, fmt, mean, median, mqr, paired, paired_str, pct, side_by_side, wr

GEM_BUCKETS = [(0, 0, '0'), (1, 35, '1-35'), (36, 69, '36-69'), (70, 10**9, '70+')]
RISK_LEVELS = [0.5, 1, 2, 4, 8, 16, 32, 64, 128]

METRICS = {
    'fights_per100': ('engagements per 100 rounds', None, True),
    'fight_win': ('engagements won on net swing (kill gems + 0.25 x kill gold - own bags lost)', True, True),
    'fight_kill_win': ('engagements won on kills (more kills)', True, True),
    'swing_per100': ('net engagement swing per 100 rounds (gem equivalents)', True, True),
    'init_share': ('engagements initiated', None, True),
    'kills_per100': ('champion kills per 100 rounds', True, True),
    'deaths_per100': ('deaths per 100 rounds (all causes)', False, True),
    'kill_gems_per100': ('gems taken from kills per 100 rounds', True, True),
    'death_gems_per100': ('own carried gems lost on death per 100 rounds', False, True),
    'bush_time': ('share of alive time on bush tiles', None, False),
    'bush_dmg': ('share of champion damage dealt from bushes', None, True),
    'unseen_time': ('share of alive time unseen by enemies', None, True),
}


def gem_bucket(x):
    for i, (lo, hi, _) in enumerate(GEM_BUCKETS):
        if lo <= x <= hi:
            return i
    return len(GEM_BUCKETS) - 1


def _find(par, i):
    while par[i] != i:
        par[i] = par[par[i]]
        i = par[i]
    return i


def _cluster(inst, radius, gap):
    n = len(inst)
    par = list(range(n))
    for j in range(n):
        sj, rj, aj, vj, _, apj, vpj = inst[j]
        pj = [p for p in (apj, vpj) if p]
        i = j - 1
        while i >= 0 and rj - inst[i][1] <= gap:
            si, ri, ai, vi, _, api, vpi = inst[i]
            pi = [q for q in (api, vpi) if q]
            near = min((chebyshev(p, q) for p in pj for q in pi), default=99)
            if ({ai, vi} & {aj, vj} and near <= 2 * radius) or (near <= radius and rj - ri <= 1):
                par[_find(par, j)] = _find(par, i)
            i -= 1
    clusters = defaultdict(list)
    for j in range(n):
        clusters[_find(par, j)].append(inst[j])
    return list(clusters.values())


def _split(its, max_dur):
    """Split an over-long cluster at rounds with no damage. Returns segments."""
    its.sort()
    if its[-1][1] - its[0][1] + 1 <= max_dur:
        return [its]
    segs, cur = [], [its[0]]
    for it in its[1:]:
        if it[1] - cur[-1][1] >= 2:
            segs.append(cur)
            cur = []
        cur.append(it)
    segs.append(cur)
    return segs


def engagements(g, P=None):
    P = P or params_mod.DEFAULTS
    radius, gap = P['radius'], P['gap']
    inst = []
    for s, r, a, v, amt, ap, vp in g.champ_damage:
        i = g.start_idx(r)
        ap = ap or g.pos(a, i)
        vp = vp or g.pos(v, i)
        inst.append((s, r, a, v, amt, ap, vp))
    raw = _cluster(inst, radius, gap)
    clusters, n_split = [], 0
    for its in raw:
        segs = _split(its, P['max_dur'])
        n_split += len(segs) > 1
        clusters += segs
    step_cluster = {}
    for cid, its in enumerate(clusters):
        for it in its:
            step_cluster[it[0]] = cid
    deaths_by = defaultdict(list)
    for e in g.deaths:
        if 'by' in e and e['s'] in step_cluster:
            deaths_by[step_cluster[e['s']]].append(e)
    stuns = []
    for e in g.events:
        if e['k'] in ('attack', 'cast') and e.get('stun'):
            vs = [v for v in e['stun'] if v in g.team_of and g.team_of[v] != g.team_of[e['a']]]
            if vs:
                stuns.append((e['r'], e['a'], vs))
    lam = P['gold_gems']
    out = []
    for cid, its in enumerate(clusters):
        its.sort()
        r0, r1 = its[0][1], its[-1][1]
        part = [set(), set()]
        dmg = [0.0, 0.0]
        pts, pts0 = [], []
        for s, r, a, v, amt, ap, vp in its:
            part[g.team_of[a]].add(a)
            part[g.team_of[v]].add(v)
            dmg[g.team_of[a]] += amt
            pts += [p for p in (ap, vp) if p]
            if r == r0:
                pts0 += [p for p in (ap, vp) if p]
        if not pts:
            continue
        loc = (round(mean([p[0] for p in pts])), round(mean([p[1] for p in pts])))
        loc0 = (round(mean([p[0] for p in pts0])), round(mean([p[1] for p in pts0]))) if pts0 else loc
        i0 = g.start_idx(r0)
        present, hp, hpmax, carried, earned, ready = [0, 0], [0.0, 0.0], [0.0, 0.0], [0, 0], [0, 0], [0, 0]
        for t in (0, 1):
            for c in g.team_ids[t]:
                p = g.pos(c, i0)
                if p and chebyshev(p, loc0) <= radius:
                    ch = g.ch(c)
                    present[t] += 1
                    hp[t] += ch['hp'][i0]
                    hpmax[t] += ch['maxHp'][i0]
                    carried[t] += ch['gems'][i0]
                    earned[t] += ch['earned'][i0]
                    ready[t] += (ch['cd0'][i0] == 0) + (ch['cd1'][i0] == 0)
        kills, gems, gold, lost, killed = [0, 0], [0, 0], [0, 0], [0, 0], []
        for e in deaths_by.get(cid, []):
            kt = g.team_of[e['by']]
            lost[1 - kt] += e['gems']
            if 'linked' in e:
                continue
            kills[kt] += 1
            gems[kt] += e.get('gemsTo', 0)
            gold[kt] += e.get('gold', 0)
            killed.append(e['v'])
        allp = part[0] | part[1]
        camp_deaths = [e for e in g.deaths if 'camp' in e and r0 <= e['r'] <= r1 + 1 and e['v'] in allp]
        for e in camp_deaths:
            lost[g.team_of[e['v']]] += e['gems']
        st = [0, 0]
        for r, a, vs in stuns:
            if r0 <= r <= r1 and a in allp:
                st[g.team_of[a]] += len(vs)
        value = [gems[t] - lost[t] + lam * gold[t] for t in (0, 1)]
        bush_init = its[0][5] in g.map.bushes if its[0][5] else False
        out.append({'dir': g.dir, 'map': g.map_name, 'r0': r0, 'r1': r1, 'loc': loc, 'init': g.team_of[its[0][2]],
                    'init_from_bush': bush_init, 'part': [len(part[0]), len(part[1])], 'present': present,
                    'hp': hp, 'hpfrac': [hp[t] / hpmax[t] if hpmax[t] else None for t in (0, 1)], 'carried': carried,
                    'earned': earned, 'ready': ready, 'dmg': dmg, 'kills': kills, 'kill_gems': gems, 'kill_gold': gold,
                    'bags_lost': lost, 'camp_deaths': [sum(1 for e in camp_deaths if g.team_of[e['v']] == t) for t in (0, 1)],
                    'stuns': st, 'half': g.map.half(loc0), 'n': len(its), 'swing': value[0] - value[1],
                    'ids': [sorted(part[0]), sorted(part[1])], 'killed': killed})
    out.sort(key=lambda f: f['r0'])
    return out, {'raw': len(raw), 'split': n_split, 'final': len(out)}


def extract(g, P=None):
    P = P or params_mod.DEFAULTS
    SEEN_K = P['seen_k']
    mp = g.map
    fights, split = engagements(g, P)
    sides = []
    risk = [defaultdict(lambda: [0, 0]) for _ in (0, 1)]
    time = [defaultdict(lambda: [0, 0]) for _ in (0, 1)]
    wards = [Counter(), Counter()]
    tributes = [Counter(), Counter()]
    altars = [Counter(), Counter()]
    bush = [[0, 0, 0, 0, 0.0, 0.0] for _ in (0, 1)]
    n = g.n_rounds
    for t in (0, 1):
        for cid in g.team_ids[t]:
            ch = g.ch(cid)
            seen = [1 if x else 0 for x in ch['sees']]
            recent = []
            acc = 0
            for i in range(len(seen)):
                acc += seen[i]
                if i >= SEEN_K:
                    acc -= seen[i - SEEN_K]
                recent.append(acc > 0)
            for r in range(2, n + 1):
                i = r - 2
                if not ch['alive'][i] or ch['x'][i] is None:
                    continue
                p = (ch['x'][i], ch['y'][i])
                c = mp.cell_of(mp.own(t, p))
                key = (c, gem_bucket(ch['gems'][i]), recent[r - 1])
                risk[t][key][0] += 1
                tm = time[t][c]
                tm[0] += 1
                if not ch['seenBy'][r - 1]:
                    tm[1] += 1
                if p in mp.bushes:
                    bush[t][0] += 1
                bush[t][1] += 1
    for e in g.deaths:
        if 'linked' in e:
            continue
        t = g.team_of[e['v']]
        c = mp.cell_of(mp.own(t, e['at']))
        r = e['r']
        rec = g.seen_recently(e['v'], r, SEEN_K)
        risk[t][(c, gem_bucket(e['gems']), rec)][1] += 1
        if tuple(e['at']) in mp.bushes:
            bush[t][2] += 1
        bush[t][3] += 1
    for s, r, a, v, amt, ap, vp in g.champ_damage:
        t = g.team_of[a]
        bush[t][5] += amt
        if ap and ap in mp.bushes:
            bush[t][4] += amt
    for e in g.events:
        if e['k'] == 'ward':
            t = g.team_of[e['a']]
            wards[t][mp.cell_of(mp.own(t, e['to']))] += 1
        elif e['k'] == 'tribute_start':
            t = g.team_of[e['a']]
            tributes[t][mp.cell_of(mp.own(t, e['at']))] += 1
            altars[t][mp.own(t, e['altar'])] += 1
    for t in (0, 1):
        mine = [f for f in fights]
        sg = 1 if t == 0 else -1
        dec = [f for f in mine if f['swing'] != 0]
        won = sum(1 for f in dec if sg * f['swing'] > 0)
        kdec = [f for f in mine if f['kills'][0] != f['kills'][1]]
        deaths = [e for e in g.deaths if g.team_of[e['v']] == t and 'linked' not in e]
        kills = [e for e in g.deaths if 'by' in e and g.team_of.get(e['by']) == t and 'linked' not in e]
        own_lost = sum(e['gems'] for e in g.deaths if g.team_of[e['v']] == t)
        b = bush[t]
        sides.append({
            'fights_per100': 100 * len(mine) / n,
            'fight_win': won / len(dec) if dec else None,
            'fight_dec': len(dec), 'fight_won': won,
            'fight_kill_win': sum(1 for f in kdec if f['kills'][t] > f['kills'][1 - t]) / len(kdec) if kdec else None,
            'swing_per100': 100 * sum(sg * f['swing'] for f in mine) / n,
            'init_share': sum(1 for f in mine if f['init'] == t) / len(mine) if mine else None,
            'kills_per100': 100 * len(kills) / n,
            'deaths_per100': 100 * len(deaths) / n,
            'kill_gems_per100': 100 * sum(e.get('gemsTo', 0) for e in kills) / n,
            'death_gems_per100': 100 * own_lost / n,
            'bush_time': b[0] / b[1] if b[1] else None,
            'bush_dmg': b[4] / b[5] if b[5] else None,
            'bush_raw': b,
            'unseen_time': sum(v[1] for v in time[t].values()) / max(1, sum(v[0] for v in time[t].values())),
            'risk': {k: v for k, v in risk[t].items()},
            'time': {k: v for k, v in time[t].items()},
            'wards': dict(wards[t]), 'tributes': dict(tributes[t]), 'altars': dict(altars[t]),
        })
    return {'sides': sides, 'fights': fights, 'split': split}


FEATURES = [
    ('present', 'more champions present (within radius at start)', lambda f: f['present'][0] - f['present'][1]),
    ('hp', 'more HP present at start', lambda f: f['hp'][0] - f['hp'][1]),
    ('hpfrac', 'higher HP fraction present', lambda f: (f['hpfrac'][0] or 0) - (f['hpfrac'][1] or 0)),
    ('gold', 'more lifetime gold present (items)', lambda f: f['earned'][0] - f['earned'][1]),
    ('carried', 'more carried gems present', lambda f: f['carried'][0] - f['carried'][1]),
    ('ready', 'more abilities off cooldown', lambda f: f['ready'][0] - f['ready'][1]),
    ('own_half', 'fight in own half', lambda f: 1 if f['half'] == 0 else -1 if f['half'] == 1 else 0),
    ('initiator', 'the initiative (dealt first damage)', lambda f: 1 if f['init'] == 0 else -1),
]
UNIVARIATE_MIN = {'hp': lambda f: 0.1 * max(1, f['hp'][0] + f['hp'][1]), 'hpfrac': lambda f: 0.1,
                  'gold': lambda f: 0.2 * max(1, max(f['earned'])), 'carried': lambda f: 10}


def _solve(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[piv] = M[piv], M[c]
        if abs(M[c][c]) < 1e-12:
            return [0.0] * n
        for r in range(n):
            if r != c:
                k = M[r][c] / M[c][c]
                if k:
                    for j in range(c, n + 1):
                        M[r][j] -= k * M[c][j]
    return [M[i][n] / M[i][i] for i in range(n)]


def logit_fit(X, y, beta=None, iters=8, ridge=1.0):
    """Ridge-penalised (intercept excluded) logistic regression by Newton/IRLS. X rows start with a 1."""
    p = len(X[0])
    beta = list(beta) if beta else [0.0] * p
    for _ in range(iters):
        g = [0.0] * p
        H = [[0.0] * p for _ in range(p)]
        for xi, yi in zip(X, y):
            eta = sum(b * x for b, x in zip(beta, xi))
            mu = 1 / (1 + math.exp(-max(-30, min(30, eta))))
            w = mu * (1 - mu)
            r = yi - mu
            for a in range(p):
                xa = xi[a]
                g[a] += r * xa
                wa = w * xa
                Ha = H[a]
                for b in range(a, p):
                    Ha[b] += wa * xi[b]
        for a in range(p):
            for b in range(a):
                H[a][b] = H[b][a]
            if a:
                H[a][a] += ridge
                g[a] -= ridge * beta[a]
        d = _solve(H, g)
        beta = [b + x for b, x in zip(beta, d)]
        if max(abs(x) for x in d) < 1e-6:
            break
    return beta


def _boot_task(args):
    X, y, groups, beta0, seeds = args
    out = []
    for sd in seeds:
        rng = random.Random(sd)
        idx = []
        for i in rng.choices(range(len(groups)), k=len(groups)):
            idx += groups[i]
        out.append(logit_fit([X[i] for i in idx], [y[i] for i in idx], beta0, iters=4))
    return out


def design(fights):
    raw = [[fn(f) for _, _, fn in FEATURES] for f in fights]
    cols = list(zip(*raw))
    mu = [mean(c) for c in cols]
    sd = [max(1e-9, (sum((x - m) ** 2 for x in c) / max(1, len(c) - 1)) ** 0.5) for c, m in zip(cols, mu)]
    return [[1.0] + [(x - m) / s for x, m, s in zip(r, mu, sd)] for r in raw], mu, sd


def logistic(fights, outcome, clusters=None, B=0, threads=1, seed=1):
    fs = [f for f in fights if outcome(f) is not None]
    if len(fs) < 50:
        return None
    X, mu, sd = design(fs)
    y = [1 if outcome(f) else 0 for f in fs]
    beta = logit_fit(X, y)
    ci = None
    if B and clusters:
        groups = list(by_cluster([(clusters(f), i) for i, f in enumerate(fs)]).values())
        seeds = [seed * 100003 + i for i in range(B)]
        k = max(1, threads)
        chunks = [c for c in (seeds[i::k] for i in range(k)) if c]
        res = []
        if threads > 1:
            with ProcessPoolExecutor(max_workers=threads) as ex:
                for part in ex.map(_boot_task, [(X, y, groups, beta, c) for c in chunks]):
                    res += part
        else:
            res = _boot_task((X, y, groups, beta, seeds))
        ci = []
        for j in range(len(beta)):
            v = sorted(r[j] for r in res)
            ci.append((v[int(0.025 * len(v))], v[min(len(v) - 1, int(0.975 * len(v)))]))
    return {'n': len(fs), 'beta': beta, 'ci': ci, 'sd': sd, 'mean_y': mean(y)}


def univariate(fights, key, outcome, cluster):
    fn = next(f for k, _, f in FEATURES if k == key)
    lim = UNIVARIATE_MIN.get(key, lambda f: 0)
    items = []
    for f in fights:
        o = outcome(f)
        if o is None:
            continue
        d = fn(f)
        if d == 0 or abs(d) <= lim(f):
            continue
        items.append((cluster(f), int(o == (d > 0))))
    return items


OUTCOMES = {
    'swing': ('net swing > 0 (fights with non-zero swing)', lambda f: None if f['swing'] == 0 else f['swing'] > 0),
    'kills': ('more kills (fights with kills)', lambda f: None if f['kills'][0] == f['kills'][1] else f['kills'][0] > f['kills'][1]),
    'damage': ('more damage dealt (all fights)', lambda f: None if f['dmg'][0] == f['dmg'][1] else f['dmg'][0] > f['dmg'][1]),
}


def headlines(ctx_games, data, P):
    """Key fight and risk numbers, for the sensitivity report."""
    games = {gi['dir']: gi for gi in ctx_games}
    fights = [f for gi in ctx_games for f in data[gi['dir']]['fights']['fights']]
    cl = lambda f: games[f['dir']]['cluster']
    out = {'engagements': len(fights), 'max duration': max((f['r1'] - f['r0'] + 1 for f in fights), default=0),
           'non-zero swing share': mean([f['swing'] != 0 for f in fights])}
    for key, name, _ in FEATURES:
        items = univariate(fights, key, OUTCOMES['swing'][1], cl)
        out[f'univariate swing win: {key}'] = mean([w for _, w in items])
    res = logistic(fights, OUTCOMES['swing'][1])
    if res:
        for j, (key, _, _) in enumerate(FEATURES, 1):
            out[f'logit coef: {key}'] = res['beta'][j]
    tot = defaultdict(lambda: [0, 0])
    for gi in ctx_games:
        for t in (0, 1):
            for (c, gb, sn), (a, d) in data[gi['dir']]['fights']['sides'][t]['risk'].items():
                tot[sn][0] += a
                tot[sn][1] += d
    out['deaths/1000 unseen'] = 1000 * tot[False][1] / max(1, tot[False][0])
    out['deaths/1000 enemy seen'] = 1000 * tot[True][1] / max(1, tot[True][0])
    return out


def render(ctx, rep):
    P = ctx.params
    SEEN_K, RADIUS, GAP = P['seen_k'], P['radius'], P['gap']
    sides = ctx.side_metrics()
    maps = sorted({s['map'] for s in sides})
    games = {gi['dir']: gi for gi in ctx.games}
    fights = [f for gi in ctx.games for f in ctx.game_data(gi, 'fights')]
    cl = lambda f: games[f['dir']]['cluster']
    split = [ctx.data[gi['dir']]['fights']['split'] for gi in ctx.games]

    rep.p(CAVEAT)
    rep.p(f'Set: {ctx.describe()}.',
          f'Engagement = champion-on-champion damage instances, single-link clustered: two instances link if they share a champion, are within {GAP} rounds '
          f'and within {2 * RADIUS} tiles, or are within 1 round and {RADIUS} tiles (Chebyshev). Clusters longer than {P["max_dur"]} rounds are split at rounds '
          f'with no damage ({sum(x["split"] for x in split)} of {sum(x["raw"] for x in split)} clusters split; {len(fights)} engagements after splitting). '
          f'Start state (used for all predictors) = alive champions within {RADIUS} tiles of the first round\'s damage centroid at the start of that round. '
          'Kills are champion kills whose killing step is one of the fight\'s damage steps (Cassi/Issac partner deaths count once). '
          f'Net swing for a side = gems taken from kills - own bags lost (kills and camp deaths during the fight) + {P["gold_gems"]} x kill gold '
          '(about the gems-per-gold rate of wolf and elk camps); it ignores the 60 rounds a dead champion stops farming.')

    rep.h('Engagement overview')
    rows = []
    for mname in maps + ['(all)']:
        fs = [f for f in fights if mname == '(all)' or f['map'] == mname]
        if not fs:
            continue
        kf = [f for f in fs if sum(f['kills'])]
        nz = [f for f in fs if f['swing'] != 0]
        gs = {f['dir'] for f in fs}
        rnds = sum(games[d]['rounds'] for d in gs)
        rows.append([mname, len(fs), fmt(100 * len(fs) / max(1, rnds), 2), len(kf), pct(len(nz) / len(fs)),
                     mqr([f['r1'] - f['r0'] + 1 for f in fs], 0), max(f['r1'] - f['r0'] + 1 for f in fs), mqr([sum(f['dmg']) for f in fs], 0),
                     mqr([abs(f['swing']) for f in nz], 0)])
    rep.table(['map', 'engagements', 'per 100 rounds', 'with kills', 'non-zero swing', 'duration (rounds)', 'max duration', 'total damage', '|swing| when non-zero'],
              rows, 'overview')

    rep.h('What predicts winning a fight')
    rep.p('Only start-of-fight state is used (stuns and participant counts happen during the fight, so they are partly the outcome; stuns are shown as description below). '
          'Univariate: among fights where the sides differ on the advantage (HP by >10% of the total, HP fraction by >0.1, gold by >20%, carried gems by >10), how often '
          'the side with it won, for three outcome definitions. Cells: win % (n fights, c clusters, 95% cluster-bootstrap CI).')
    rows = []
    for key, name, _ in FEATURES:
        row = [name]
        for ok, (oname, ofn) in OUTCOMES.items():
            items = univariate(fights, key, ofn, cl)
            row.append(cwr(items))
            if ok == 'swing' and len(items) >= 30:
                rep.highlight(f'Fights (start state, net-swing outcome): the side with {name} won {cwr(items)}.')
        rows.append(row)
    rep.table(['advantage at start'] + [o[0] for o in OUTCOMES.values()], rows, 'predictors')
    sw = [f for f in fights if f['swing'] != 0]
    st_items = [(cl(f), int((f['stuns'][0] > f['stuns'][1]) == (f['swing'] > 0))) for f in sw if f['stuns'][0] != f['stuns'][1]]
    rep.p(f'Descriptive only: the side that landed more stuns during the fight also won the swing in {cwr(st_items)}.')

    res = logistic(fights, OUTCOMES['swing'][1], cl, B=200, threads=ctx.threads, seed=P['seed'])
    res_d = logistic(fights, OUTCOMES['damage'][1])
    if res:
        rep.p(f'Logistic regression of team A winning the net swing on standardized start-state differences (A minus B), ridge 1.0, n={res["n"]} fights. '
              'Coefficient = change in log-odds per standard deviation of the difference with the others held fixed, so correlated advantages '
              '(numbers, HP and gold move together) are not counted three times. CIs: 200 cluster-bootstrap refits. The last column fits the same model to '
              'the damage-margin outcome (all fights with unequal damage; point estimates).')
        rows = [['intercept (team A)', fmt(res['beta'][0], 2), f'{fmt(res["ci"][0][0], 2)}..{fmt(res["ci"][0][1], 2)}' if res['ci'] else '-', '-',
                 fmt(res_d['beta'][0], 2) if res_d else '-']]
        for j, (key, name, _) in enumerate(FEATURES, 1):
            lo, hi = res['ci'][j] if res['ci'] else (None, None)
            rows.append([name, fmt(res['beta'][j], 2), f'{fmt(lo, 2)}..{fmt(hi, 2)}', fmt(res['sd'][j - 1], 1), fmt(res_d['beta'][j], 2) if res_d else '-'])
        rep.table(['start-state difference (A - B)', 'coef (log-odds / SD)', '95% CI', '1 SD =', 'coef, damage outcome'], rows, 'logistic')
        strong = [(abs(res['beta'][j]), name, res['beta'][j], res['ci'][j]) for j, (key, name, _) in enumerate(FEATURES, 1)
                  if res['ci'] and (res['ci'][j][0] > 0 or res['ci'][j][1] < 0)]
        strong.sort(reverse=True)
        if strong:
            rep.highlight('Fights, logistic on start state (net swing): CI excludes 0 for ' + '; '.join(
                f'{n} {b:+.2f} [{c[0]:+.2f}, {c[1]:+.2f}]' for _, n, b, c in strong) + f' (log-odds per SD, n={res["n"]}).')
    rows = []
    for d in range(-3, 4):
        fs = [f for f in sw if max(-3, min(3, f['present'][0] - f['present'][1])) == d]
        rows.append([f'{d:+d}' if d not in (-3, 3) else f'{d:+d} or more', cwr([(cl(f), int(f['swing'] > 0)) for f in fs])])
    rep.p('Team A\'s net-swing win % by its numbers advantage at the start:')
    rep.table(['numbers', 'team A win %'], rows)

    rep.h('Fight record per side')
    rows = []
    for mname in maps + ['(all)']:
        ms = [s for s in sides if mname == '(all)' or s['map'] == mname]
        w = [s for s in ms if s['won']]
        l = [s for s in ms if not s['won']]
        rows.append([mname, mqr([s['fights_per100'] for s in ms], 2),
                     f'{pct(sum(s["fight_won"] for s in w) / max(1, sum(s["fight_dec"] for s in w)))} / {pct(sum(s["fight_won"] for s in l) / max(1, sum(s["fight_dec"] for s in l)))}',
                     f'{fmt(mean([s["swing_per100"] for s in w]), 1)} / {fmt(mean([s["swing_per100"] for s in l]), 1)}',
                     f'{fmt(mean([s["kills_per100"] for s in w]), 2)} / {fmt(mean([s["kills_per100"] for s in l]), 2)}',
                     f'{fmt(mean([s["deaths_per100"] for s in w]), 2)} / {fmt(mean([s["deaths_per100"] for s in l]), 2)}',
                     f'{pct(median([s["init_share"] for s in w]))} / {pct(median([s["init_share"] for s in l]))}'])
    rep.table(['map', 'engagements/100r', 'net-swing fights won W / L', 'mean swing/100r W / L', 'mean kills/100r W / L', 'mean deaths/100r W / L', 'initiated W / L'],
              rows, 'record')
    p = paired(ctx.pairs('deaths_per100'))
    if p and p['n'] >= 20:
        rep.highlight(f'Deaths per 100 rounds, same game (partly a consequence of winning): {paired_str(p, lower_better=True)}.')

    rep.h('Largest engagements')
    rep.p('By |net swing|, then damage. Location is in team A\'s frame; swing is for team A.')
    big = sorted(fights, key=lambda f: (-abs(f['swing']), -sum(f['dmg'])))[:25]
    rows = []
    for f in big:
        gi = games[f['dir']]
        rows.append([f'{f["dir"]} r{f["r0"]}-{f["r1"]}', gi['map'], f'{gi["names"][0]} vs {gi["names"][1]}', f'{f["present"][0]}v{f["present"][1]}',
                     f'{f["hp"][0]:.0f}/{f["hp"][1]:.0f}', f'{f["kills"][0]}-{f["kills"][1]}', f'{f["kill_gems"][0]}/{f["kill_gems"][1]}',
                     f'{f["bags_lost"][0]}/{f["bags_lost"][1]}', f'{f["swing"]:+.0f}', f'{f["loc"][0]},{f["loc"][1]}', 'A' if f['init'] == 0 else 'B'])
    rep.table(['game rounds', 'map', 'teams', 'present at start', 'HP A/B', 'kills A-B', 'kill gems A/B', 'bags lost A/B', 'swing (A)', 'location', 'initiator'], rows)
    csv = []
    for f in fights:
        gi = games[f['dir']]
        csv.append([f['dir'], f['map'], gi['names'][0], gi['names'][1], f['r0'], f['r1'], f['loc'][0], f['loc'][1], f['init'], f['part'][0], f['part'][1],
                    f['present'][0], f['present'][1], round(f['hp'][0]), round(f['hp'][1]), f['ready'][0], f['ready'][1], f['kills'][0], f['kills'][1],
                    f['kill_gems'][0], f['kill_gems'][1], f['kill_gold'][0], f['kill_gold'][1], f['bags_lost'][0], f['bags_lost'][1], f['stuns'][0], f['stuns'][1],
                    round(f['dmg'][0]), round(f['dmg'][1]), round(f['swing'], 1), ' '.join(map(str, f['ids'][0])), ' '.join(map(str, f['ids'][1]))])
    rep.write_csv('engagements', ['dir', 'map', 'team_a', 'team_b', 'r0', 'r1', 'x', 'y', 'initiator', 'part_a', 'part_b', 'present_a', 'present_b', 'hp_a', 'hp_b',
                                  'ready_a', 'ready_b', 'kills_a', 'kills_b', 'kill_gems_a', 'kill_gems_b', 'kill_gold_a', 'kill_gold_b', 'bags_lost_a', 'bags_lost_b',
                                  'stuns_a', 'stuns_b', 'dmg_a', 'dmg_b', 'swing_a', 'ids_a', 'ids_b'], csv)

    rep.h('Death risk')
    rep.p(f'Deaths per 1000 champion-rounds, own-side frame (team B mirrored onto A), from the side\'s own deaths (any cause; Cassi/Issac partner deaths excluded) '
          f'over its alive champion-rounds (position at the start of the round). "Enemy seen" = the champion saw an enemy champion at the start of one of its '
          f'last {SEEN_K} turns. Gem bucket: start-of-round bag for exposure, bag at death for deaths.')
    agg_rows = []
    for mname in maps + ['(all)']:
        ms = [s for s in sides if mname == '(all)' or s['map'] == mname]
        tot = defaultdict(lambda: [0, 0])
        for s in ms:
            for (c, gb, sn), (a, d) in s['risk'].items():
                tot[(gb, sn)][0] += a
                tot[(gb, sn)][1] += d
        row = [mname]
        for sn in (False, True):
            for gb in range(len(GEM_BUCKETS)):
                a, d = tot[(gb, sn)]
                row.append(f'{1000 * d / a:.1f} ({d}/{a})' if a else '-')
        agg_rows.append(row)
    hdr = ['map'] + [f'{"seen" if sn else "unseen"} {b[2]}' for sn in (False, True) for b in GEM_BUCKETS]
    rep.table(hdr, agg_rows, 'risk_buckets')
    rep.p('Columns: enemy seen in last turns (no/yes) x carried gems. Cell = deaths per 1000 champion-rounds (deaths/rounds).')
    allr = defaultdict(lambda: [0, 0])
    for s in sides:
        for (c, gb, sn), (a, d) in s['risk'].items():
            allr[(gb >= 2, sn)][0] += a
            allr[(gb >= 2, sn)][1] += d
    if allr[(False, True)][0] and allr[(True, True)][0]:
        a0, d0 = allr[(False, True)]
        a1, d1 = allr[(True, True)]
        u0, v0 = allr[(False, False)]
        rep.highlight(f'Death risk per 1000 champion-rounds: {1000 * v0 / max(1, u0):.1f} when no enemy was seen in the last {SEEN_K} turns ({v0} deaths), '
                      f'{1000 * d0 / max(1, a0):.1f} after seeing one with <36 gems ({d0}), {1000 * d1 / max(1, a1):.1f} after seeing one with 36+ gems ({d1}).')

    rep.p('Heatmap scale (deaths per 1000 champion-rounds): ' + ', '.join(f'`{c}` >= {t}' for c, t in zip(' .:-=+*#%@'[1:], RISK_LEVELS)) +
          '; blank = fewer than 30 champion-rounds or not reached. Landmarks: S own spawn, X enemy spawn, A altar, w/e/g/$/M camps, # wall, ~ bush, o hole. North is up.')
    csv = []
    for mname in maps:
        mp = ctx.map_of(mname)
        ms = [s for s in sides if s['map'] == mname]
        grids, titles = [mp_lines(mp)], ['landmarks']
        for title, pred in (('all deaths', lambda gb, sn: True), ('carrying 36+', lambda gb, sn: gb >= 2), ('enemy seen recently', lambda gb, sn: sn)):
            vals, mask = {}, set()
            exp = defaultdict(lambda: [0, 0])
            for s in ms:
                for (c, gb, sn), (a, d) in s['risk'].items():
                    if pred(gb, sn):
                        exp[c][0] += a
                        exp[c][1] += d
            for c, (a, d) in exp.items():
                if a >= 30:
                    vals[c] = 1000 * d / a
                    mask.add(c)
                if pred is not None and title == 'all deaths':
                    csv.append([mname, c[0], c[1], a, d])
            grids.append(ascii_grid(mp, vals, RISK_LEVELS, mask))
            titles.append(title)
        rep.h(f'{mname} (cell = {mp.cell}x{mp.cell} tiles, {len(ms)} sides)', 3)
        rep.code(side_by_side(grids, titles))
        hot = sorted(((1000 * d / a, c, a, d) for c, (a, d) in _cells(ms).items() if a >= 100 and d >= 3), reverse=True)[:3]
        if hot:
            rep.p('Hottest cells: ' + '; '.join(f'cell ({c[0] * mp.cell}-{c[0] * mp.cell + mp.cell - 1}, {c[1] * mp.cell}-{c[1] * mp.cell + mp.cell - 1}) '
                                                 f'{rt:.1f}/1000 ({d} deaths / {a} rounds)' for rt, c, a, d in hot))
    rep.write_csv('risk_cells', ['map', 'cx', 'cy', 'champion_rounds', 'deaths'], csv)

    rep.h('Where sides spend time, tribute and ward')
    rep.p('Per map, own-side frame. Time = alive champion-rounds per cell, scaled to the busiest cell; unseen = share of those rounds no enemy saw the champion '
          '(`@` >= 90%, `.` < 20%); tributes = tribute starts; wards = ward placements (both scaled to the busiest cell).')
    for mname in maps:
        mp = ctx.map_of(mname)
        ms = [s for s in sides if s['map'] == mname]
        tm, wd, tb = defaultdict(lambda: [0, 0]), Counter(), Counter()
        for s in ms:
            for c, (a, u) in s['time'].items():
                tm[c][0] += a
                tm[c][1] += u
            wd.update(s['wards'])
            tb.update(s['tributes'])
        mx = max([v[0] for v in tm.values()] or [1])
        rel = lambda cnt, m: {c: v / m for c, v in cnt.items()}
        lv = [0.001, 0.01, 0.03, 0.06, 0.12, 0.25, 0.5, 0.75, 0.95]
        g_time = ascii_grid(mp, rel({c: v[0] for c, v in tm.items()}, mx), lv)
        g_unseen = ascii_grid(mp, {c: v[1] / v[0] for c, v in tm.items() if v[0] >= 30}, [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.9])
        g_trib = ascii_grid(mp, rel(tb, max(tb.values() or [1])), lv)
        g_ward = ascii_grid(mp, rel(wd, max(wd.values() or [1])), lv)
        rep.h(f'{mname}', 3)
        rep.code(side_by_side([mp_lines(mp), g_time, g_unseen, g_trib, g_ward], ['landmarks', 'time', 'unseen share', 'tributes', 'wards']))
        alt = Counter()
        altw, altl = Counter(), Counter()
        for s in ms:
            alt.update(s['altars'])
            (altw if s['won'] else altl).update(s['altars'])
        if alt:
            sc = mp.spawn_center(0)
            rows = []
            tot, tw, tl = sum(alt.values()), max(1, sum(altw.values())), max(1, sum(altl.values()))
            for a, k in sorted(alt.items(), key=lambda kv: chebyshev(kv[0], sc)):
                rows.append([f'{a[0]},{a[1]}', round(chebyshev(a, sc)), k, pct(k / tot), pct(altw[a] / tw), pct(altl[a] / tl)])
            rep.p('Tribute altars (own frame, by distance from own spawn centre):')
            rep.table(['altar', 'dist', 'tributes', 'share', 'share W', 'share L'], rows)

    rep.h('Bush usage')
    rows = []
    for mname in maps + ['(all)']:
        ms = [s for s in sides if mname == '(all)' or s['map'] == mname]
        w = [s for s in ms if s['won']]
        l = [s for s in ms if not s['won']]
        b = [sum(s['bush_raw'][i] for s in ms) for i in range(6)]
        in_rate = 1000 * b[2] / b[0] if b[0] else None
        out_rate = 1000 * (b[3] - b[2]) / (b[1] - b[0]) if b[1] - b[0] else None
        rows.append([mname, f'{pct(median([s["bush_time"] for s in w]), 1)} / {pct(median([s["bush_time"] for s in l]), 1)}',
                     f'{pct(median([s["bush_dmg"] for s in w]), 1)} / {pct(median([s["bush_dmg"] for s in l]), 1)}',
                     f'{fmt(in_rate, 2)} ({b[2]})', f'{fmt(out_rate, 2)} ({b[3] - b[2]})'])
    rep.table(['map', 'time in bush W / L', 'champion damage from bush W / L', 'deaths/1000r in bush (n)', 'outside (n)'], rows, 'bush')
    iw = lambda f: int((f['swing'] > 0) == (f['init'] == 0))
    ib = [f for f in sw if f['init_from_bush']]
    rep.p(f'Engagements with non-zero swing opened from a bush: initiator won {cwr([(cl(f), iw(f)) for f in ib])}; '
          f'all such engagements: initiator won {cwr([(cl(f), iw(f)) for f in sw])}.')


def _cells(ms):
    out = defaultdict(lambda: [0, 0])
    for s in ms:
        for (c, gb, sn), (a, d) in s['risk'].items():
            out[c][0] += a
            out[c][1] += d
    return out


def mp_lines(mp):
    return ascii_grid(mp, {}, [], landmarks=True)
