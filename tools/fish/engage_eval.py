"""Frozen rules and tables of ENGAGE.md (sections 1, 2, 4, 5, 6) on fit and held-out cohorts.

Inputs: replays/fish-engage/<cohort>-rows-v1.jsonl.gz (engage_rows.py), range-v1.jsonl.gz
(engage_range.py), retreat-v2.jsonl.gz (engage_retreat.py), the observer caches replays/fish-team/
(kill labels and outcomes only) and the actor caches (maps, for spawn tiles and terrain).
Constants were chosen on the fit cohorts (model, confirm, third, fourth) before held-out scoring.

  python3 tools/fish/engage_eval.py research/fish-2026-11-05/engage-results.json [--held fifth sixth]
    [--range R.jsonl.gz ... --retreat T.jsonl.gz ... --team-cache DIR]
"""
import argparse
import collections
import gzip
import json
import multiprocessing as mp
from pathlib import Path

from breadth import spawn
from combat_common import COHORTS, one_turn_damage
from engage_common import FIT, HELD, NAMES, REACH, ROWS, Score, free, write

CACHE = {c[0]: c[2] for c in COHORTS}
NB = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]

# Frozen constants (fit cohorts).
RETREAT_HP, RETREAT_RATIO = 0.36, 1.3     # walking retreat rule, section 2 (grid optimum on fit)
FORCED_HP = 0.5                           # forced-route proceed split, section 1
WEAK = 0.4                                # weak enemy (prey) split


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def champ(e):
    return dict(type=e['type'], strength=e['str'], focus=e['foc'], cd=e['cd'], hp=e['hp'], maxHp=e['mhp'])


def mode(nl):
    if nl is None:
        return 'quiet'
    if -5 <= nl <= -1:
        return 'early'
    if abs(nl) >= 50:
        return 'contact'
    if nl >= 5:
        return 'late'
    return 'quiet'


TEAM_CACHE = ['replays/fish-team']


def init(team_cache):
    TEAM_CACHE[0] = team_cache


def per_game(line):
    """Everything that needs the per-game engage rows: returns (cohort, dict of Counters, lists)."""
    g = json.loads(line)
    c = g['cohort']
    with gzip.open(Path(CACHE[c]) / f"{g['game']}.json.gz") as f:
        m = json.load(f)['map']
    block = set(map(tuple, m['walls'] + m['holes'] + m['altars']))
    C = collections.defaultdict(collections.Counter)
    L = collections.defaultdict(list)
    by = {int(a): {r['r']: r for r in rows} for a, rows in g['actors'].items()}
    for aid, rows in g['actors'].items():
        aid = int(aid)
        nxt = [None] * len(rows); cur = None
        for i in range(len(rows) - 1, -1, -1):
            r = rows[i]
            if not r['alive']:
                cur = None
            y = r.get('y')
            if y and y['camp']:
                cur = (r['r'], (y['ex'], y['ey']))
            nxt[i] = cur
        for i, r in enumerate(rows):
            x, y = r.get('x'), r.get('y')
            if not (x and y):
                continue
            p = (x['x'], x['y'])
            # 1e. Early mode against the end tile (all alive unstunned turns with an enemy in sight).
            if not x['stn'] and x['E']:
                md = mode(y['L'] if y['L'] is not None else x['Lstart'])
                if md != 'late':
                    ed = min(y['ed'][str(e['id'])] for e in x['E'])
                    C['early_by_end_d'][(min(ed, 9), md)] += 1
                    if md in ('quiet', 'early') and 3 <= ed <= 5:
                        me = dict(type=x['type'], strength=x['str'], focus=x['foc'], cd=x['cd'], hp=x['hp'], maxHp=x['mhp'])
                        et = any(not e['stn'] and one_turn_damage(champ(e), y['ed'][str(e['id'])]) > 0 for e in x['E'])
                        mt = any(one_turn_damage(me, y['ed'][str(e['id'])]) > 0 for e in x['E'])
                        C['early_threat'][(et, mt, md)] += 1
            if not free(x):
                continue
            # 1d. Farming continues: last turn hit a camp, an awake camp still has us in range.
            if i and rows[i - 1].get('y') and rows[i - 1]['y']['camp'] and rows[i - 1]['r'] == r['r'] - 1 and x['aggro']:
                k = 'none' if not x['E'] else f"d{x['d1']}" if x['d1'] <= 8 else 'far'
                if k in ('d1', 'd2', 'd3'):
                    k = 'd1-3'
                C['camp_continue'][(k, bool(y['camp']))] += 1
                if x['E']:
                    hk = 'hurt' if x['hp'] / x['mhp'] < 0.5 else 'ok'
                    C['camp_continue_threat'][(f"thr>0={x['thr'] > 0}" if 'thr' in x else 'na', bool(y['camp']))] += 1
                    thr = sum(q['thr'] for q in x['E'])
                    C['camp_continue_threat'][(f"enemyD>0={thr > 0}|{hk}", bool(y['camp']))] += 1
                    L['camp_rule'].append((c, g['game'], g['group'], r['r'], aid, x['type'], x['d1'], thr > 0, bool(y['camp'])))
            # 1b. Route geometry (hindsight goal: end tile of the next camp-hit turn within 40 rounds).
            if x['E'] and 4 <= x['d1'] <= 8 and not y['camp'] and x['gst'] != 2 and not y['dash']:
                nf = nxt[i + 1] if i + 1 < len(rows) else None
                if nf is not None and nf[0] - r['r'] <= 40 and cheb(p, nf[1]) > 1:
                    G = nf[1]; e = x['E'][0]; E = (e['x'], e['y'])
                    Pg = [d for d in NB if cheb((p[0] + d[0], p[1] + d[1]), G) < cheb(p, G)]
                    safe = [d for d in Pg if cheb((p[0] + d[0], p[1] + d[1]), E) >= e['d']]
                    mv = (y['ex'] - p[0], y['ey'] - p[1])
                    L['geo'].append((c, g['game'], g['group'], r['r'], aid, x['type'], 'free' if safe else 'forced',
                                     'progress' if mv in Pg else 'stay' if mv == (0, 0) else 'other', y['ed'][str(e['id'])] - e['d'],
                                     x['hp'] / x['mhp'], e['hp'] / e['mhp'], x['d1']))
            # 1c. Danger-aware steps among route-progress steps (hindsight route goal).
            if x['E'] and 3 <= x['d1'] <= 8 and not y['camp'] and x['gst'] != 2 and not y['dash'] and not y['hitc'] and y['moves'] == 1:
                nf = nxt[i + 1] if i + 1 < len(rows) else None
                if nf is not None and nf[0] - r['r'] <= 40 and cheb(p, nf[1]) > 1:
                    G = nf[1]
                    occ = {(e['x'], e['y']) for e in x['E']} | {(a['x'], a['y']) for a in x['A']}
                    P = [(p[0] + d[0], p[1] + d[1]) for d in NB]
                    P = [q for q in P if q not in block and q not in occ and 0 <= q[0] < g['W'] and 0 <= q[1] < g['H']
                         and cheb(q, G) < cheb(p, G)]
                    e1 = (y['ex'], y['ey'])
                    if e1 in P and len(P) >= 2:
                        eh = max(1, x['hp'] + x['sh'])
                        dang = {q: round(sum(0 if e['stn'] else one_turn_damage(champ(e), cheb(q, (e['x'], e['y'])))
                                             for e in x['E']) / eh, 4) for q in P}
                        if len(set(dang.values())) >= 2:
                            mn = min(dang.values())
                            hk = 'hurt' if x['hp'] / x['mhp'] < 0.5 else 'ok'
                            L['danger'].append((c, g['game'], g['group'], r['r'], aid, x['type'], hk, x['d1'],
                                                dang[e1] == mn, sum(1 for q in P if dang[q] == mn) / len(P)))
            # 4. Convergence on a fighting ally (only actor aid as the fighter).
            fighting = bool(y['hitc'])
            quiet = not x['E'] and (x['lc'] is None or x['lc'] > 10)
            if fighting or quiet:
                for B, rb in by.items():
                    if B == aid:
                        continue
                    q = rb.get(r['r'])
                    if not q or not q.get('x') or not q.get('y') or not free(q['x']):
                        continue
                    qx = q['x']
                    d0 = cheb((qx['x'], qx['y']), p)
                    if not 9 <= d0 <= 30 or any(a['id'] == aid for a in qx['A']):
                        continue
                    sees = 'sees_enemy' if (qx['E'] or qx['later']) else 'mem' if any(mm['r'] >= r['r'] - 10 for mm in qx['M']) else 'blind'
                    q5 = rb.get(r['r'] + 5)
                    if q5 and q5.get('x'):
                        d5 = cheb((q5['x']['x'], q5['x']['y']), p)
                        k = ('fight' if fighting else 'quiet', sees, min(d0 // 5 * 5, 25))
                        C['conv_n'][k] += 1; C['conv_sum'][k] += d5 - d0; C['conv_arrive'][k] += d5 <= 6
            # 6. Profiles.
            lead = x['so'] - x['sx']
            lb = 'lead>200' if lead > 200 else 'lead>0' if lead > 0 else 'tied' if lead == 0 else 'behind>-200' if lead > -200 else 'behind<=-200'
            for key in (f"round{min(r['r'] // 250 * 250, 1750)}", lb, 'opp>=800' if x['sx'] >= 800 else 'opp<800',
                        'own>=800' if x['so'] >= 800 else 'own<800', 'type:' + NAMES[x['type']]):
                k = C['profile:' + key]
                k['n'] += 1; k['enemy_visible'] += bool(x['E']); k['champ_hit'] += bool(y['hitc'])
                k['camp_hit'] += bool(y['camp']); k['tribute_start'] += bool(y['submit'] and y['ech'] == 2)
                if x['E'] and 4 <= x['d1'] <= 8 and not y['camp'] and x['gst'] != 2:
                    k['range_n'] += 1; k['range_close'] += y['ed'][str(x['E'][0]['id'])] < x['d1']
                if x['E'] and x['d1'] <= 3:
                    k['contact_n'] += 1; k['contact_hit'] += bool(y['hitc'])
    # 5. After a Fish kill (observer kill labels; Fish's own rows after it).
    with gzip.open(Path(TEAM_CACHE[0]) / f"{g['game']}.json.gz") as f:
        T = json.load(f)
    team = {q['id']: q['team'] for q in T['roster']}
    for R in T['rounds']:
        for t in R['turns']:
            for a in t['acts']:
                if not (a[0] in ('Attack', 'Cast ability') and len(a) >= 10 and a[6] == 1 and a[9] is not None and a[9] <= 0):
                    continue
                k_, v_ = t['id'], a[7]
                if team.get(k_) != g['side'] or team.get(v_) == g['side'] or k_ not in by:
                    continue
                rs = by[k_]; r0 = rs.get(R['r'])
                if not r0 or not r0.get('y'):
                    continue
                end = 'timeout'
                for j in range(R['r'] + 1, R['r'] + 41):
                    q = rs.get(j)
                    if not q:
                        continue
                    qx, qy = q.get('x'), q.get('y')
                    if not q['alive'] or not qx:
                        end = 'death'; break
                    if qx['home']:
                        end = 'home'; break
                    if not qy:
                        continue
                    if qy['hitc']:
                        end = 'fight'; break
                    if qy['submit'] and qy['ech'] == 2:
                        end = 'tribute'; break
                    if qy['camp']:
                        end = 'farm'; break
                others = len([e for e in r0['x']['E'] if e['id'] != v_])
                L['kills'].append((c, g['game'], g['group'], R['r'], k_, r0['x']['type'], r0['y']['egems'],
                                   r0['y']['ehp'] / r0['x']['mhp'], others, end))
    return c, C, L


def frac(n, k):
    return round(k / n, 4) if n else None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--held', nargs='+', default=HELD)
    p.add_argument('--range', nargs='+', default=[str(ROWS / 'range-v1.jsonl.gz')])
    p.add_argument('--retreat', nargs='+', default=[str(ROWS / 'retreat-v2.jsonl.gz')])
    p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--team-cache', default='replays/fish-team')
    a = p.parse_args()
    if Path(a.out).exists():
        raise SystemExit(f'refusing to overwrite {a.out}')
    held = a.held
    role = {c: 'fit' for c in FIT} | {c: 'held' for c in held}
    res = dict(definition=__doc__, held=held, constants=dict(RETREAT_HP=RETREAT_HP, RETREAT_RATIO=RETREAT_RATIO,
                                                              FORCED_HP=FORCED_HP, WEAK=WEAK))

    # ---- Section 1a/1b: range rows.
    S_mom = Score('range: close iff momentum closes')
    tab = collections.defaultdict(collections.Counter)
    for line in (l for fn in a.range for l in gzip.open(fn, 'rt')):
        r = json.loads(line)
        if r['cohort'] not in role:
            continue
        x, y = r['x'], r['y']
        close = y['edd'] < 0
        S_mom.add(r, x['mom'] == -1, close, base=False)
        sp = role[r['cohort']]
        hk = 'hurt' if x['hpf'] < FORCED_HP else 'ok'
        ek = 'weak' if x['ehpf'] < WEAK else 'ok'
        tab[sp][('d', x['d1'], 'close' if close else 'hold' if y['edd'] == 0 else 'open')] += 1
        tab[sp][('hp', hk, 'close' if close else 'hold' if y['edd'] == 0 else 'open')] += 1
        tab[sp][('enemy', ek, 'close' if close else 'hold' if y['edd'] == 0 else 'open')] += 1
        tab[sp][('n_e', min(x['n_e'], 3), 'close' if close else 'hold' if y['edd'] == 0 else 'open')] += 1
        if y['gdd'] is not None and y['moved'] and not y['dash']:
            tab[sp][('goal_progress_by_d', x['d1'], y['gdd'] < 0)] += 1
    res['range'] = dict(momentum=S_mom.report(held), table={k: {'|'.join(map(str, kk)): v for kk, v in t.items()} for k, t in tab.items()})
    print(S_mom.line(held))


    # ---- Per-game pass.
    C = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    Ls = collections.defaultdict(list)
    with mp.Pool(a.jobs, initializer=init, initargs=(a.team_cache,)) as pool:
        for c in FIT + held:
            with gzip.open(ROWS / f'{c}-rows-v1.jsonl.gz', 'rt') as fh:
                for cc, Cg, Lg in pool.imap_unordered(per_game, fh, chunksize=2):
                    for k, v in Cg.items():
                        C[role[cc]][k].update(v)
                    for k, v in Lg.items():
                        Ls[k] += v
            print('pass', c, flush=True)

    # 1b route geometry.
    S_forced = Score(f'forced route: progress iff hp > {FORCED_HP}')
    gt = collections.defaultdict(collections.Counter)
    for q in Ls['geo']:
        c, game, group, rnd, actor, typ, cls, act, edd, hp, ehp, d1 = q
        r = dict(cohort=c, game=game, group=group, round=rnd, actor=actor, type=typ)
        sp = role[c]
        if cls == 'forced':
            S_forced.add(r, hp > FORCED_HP, act == 'progress', base=True)
        for key in (cls, f'{cls}|d{d1}', f"{cls}|{'hurt' if hp < FORCED_HP else 'ok'}", f"{cls}|enemy {'weak' if ehp < WEAK else 'ok'}"):
            gt[sp][(key, 'n')] += 1; gt[sp][(key, act)] += 1; gt[sp][(key, 'close')] += edd < 0
    res['route_geometry'] = dict(forced_rule=S_forced.report(held), table={sp: {key: {k: frac(t[(key, 'n')], t[(key, k)])
                                 for k in ('progress', 'stay', 'other', 'close')} | dict(n=t[(key, 'n')]) for key in sorted({k for k, _ in t})}
                                 for sp, t in gt.items()})
    print(S_forced.line(held))

    # 1c danger-aware steps.
    dg = {}
    for sp in ('fit', 'held'):
        D = [d for d in Ls['danger'] if role[d[0]] == sp]
        out = {}
        for name, sel in (('all', lambda d: True), ('hurt', lambda d: d[6] == 'hurt'), ('ok', lambda d: d[6] == 'ok'),
                          ('d3', lambda d: d[7] == 3), ('d4', lambda d: d[7] == 4), ('d5', lambda d: d[7] == 5), ('d6+', lambda d: d[7] >= 6)):
            s = [d for d in D if sel(d)]
            out[name] = dict(n=len(s), chosen_min_danger=frac(len(s), sum(d[8] for d in s)),
                             random_min_danger=round(sum(d[9] for d in s) / len(s), 4) if s else None)
        dg[sp] = out
    dg['counterexamples_hurt_not_min'] = [dict(game=d[1], round=d[3], actor=d[4], type=NAMES[d[5]], d1=d[7])
                                          for d in Ls['danger'] if role[d[0]] == 'held' and d[6] == 'hurt' and not d[8]][:12]
    res['danger_steps'] = dg
    print('danger', json.dumps(dg['held']['all']), json.dumps(dg['held']['hurt']))

    # 1d camp continuation, 1e early mode.
    for sp in ('fit', 'held'):
        cc = C[sp]['camp_continue']
        res.setdefault('camp_continue', {})[sp] = {k: dict(n=cc[(k, True)] + cc[(k, False)], hit=frac(cc[(k, True)] + cc[(k, False)], cc[(k, True)]))
                                                   for k in sorted({k for k, _ in cc})}
        eb = C[sp]['early_by_end_d']
        res.setdefault('early_by_end_distance', {})[sp] = {
            d: {m: frac(sum(eb[(d, mm)] for mm in ('quiet', 'early', 'contact')), eb[(d, m)]) for m in ('quiet', 'early', 'contact')}
            | dict(n=sum(eb[(d, mm)] for mm in ('quiet', 'early', 'contact'))) for d in sorted({d for d, _ in eb})}
        et = C[sp]['early_threat']
        res.setdefault('early_threat', {})[sp] = {f'enemyD>0={k[0]},myD>0={k[1]}': dict(n=et[k + ('quiet',)] + et[k + ('early',)],
                                                    early=frac(et[k + ('quiet',)] + et[k + ('early',)], et[k + ('early',)]))
                                                  for k in sorted({k[:2] for k in et})}
    for sp in ('fit', 'held'):
        cc = C[sp]['camp_continue_threat']
        res.setdefault('camp_continue_threat', {})[sp] = {k: dict(n=cc[(k, True)] + cc[(k, False)], hit=frac(cc[(k, True)] + cc[(k, False)], cc[(k, True)]))
                                                          for k in sorted({k for k, _ in cc})}
    S_camp = Score('at a camp with an enemy in sight: keeps hitting iff no enemy one-turn damage reaches its tile')
    S_camp5 = Score('at a camp with an enemy in sight: keeps hitting iff the nearest enemy is beyond 4')
    for q in Ls['camp_rule']:
        c, game, group, rnd, actor, typ, d1, thr, hit = q
        r = dict(cohort=c, game=game, group=group, round=rnd, actor=actor, type=typ)
        S_camp.add(r, not thr, hit, base=True); S_camp5.add(r, d1 > 4, hit, base=True)
    res['camp_continue_rules'] = dict(threat=S_camp.report(held), beyond4=S_camp5.report(held))
    print(S_camp.line(held)); print(S_camp5.line(held))
    print('camp', json.dumps(res['camp_continue']['held']))
    print('early', json.dumps(res['early_threat']['held']))

    # ---- Section 2: retreat.
    S_ret = Score(f'retreat iff hp <= {RETREAT_HP} and ratio <= {RETREAT_RATIO}')
    S_acc = Score('retreat iff COMBAT unacceptable')
    rt = collections.defaultdict(collections.Counter)
    eps = collections.defaultdict(list); last = {}
    homes = {}
    rows = []
    for line in (l for fn in a.retreat for l in gzip.open(fn, 'rt')):
        r = json.loads(line)
        if r['cohort'] in role and r['y']['valid']:
            rows.append(r)
    rows.sort(key=lambda r: (r['game'], r['actor'], r['round']))
    for r in rows:
        x, y = r['x'], r['y']; sp = role[r['cohort']]
        if x['d1'] <= 1 and not x['ranged']:
            continue  # adjacent melee always strikes (COMBAT): no walking-retreat choice
        pred = x['hpf'] <= RETREAT_HP and x['ratio'] <= RETREAT_RATIO
        S_ret.add(r, pred, y['retreat'], base=False)
        S_acc.add(r, not x['acceptable'], y['retreat'], base=False)
        hk = 'hp<=0.54' if x['hpf'] <= 0.54 else 'hp>0.54'
        for name, v in (('outnumbered', 'n_e>n_a+1' if x['n_e'] > x['n_a8'] + 1 else 'n_e<=n_a' if x['n_e'] <= x['n_a8'] else 'n_e=n_a+1'),
                        ('ally_death10', x['ally_deaths10'] > 0), ('capturing', x['capturing']), ('carrying', x['gems'] > 0),
                        ('acceptable', x['acceptable'])):
            rt[sp][(name, str(v), hk, 'n')] += 1; rt[sp][(name, str(v), hk, 'retreat')] += y['retreat']
        if y['retreat']:
            k = (r['game'], r['actor'])
            if k in last and r['round'] - last[k] <= 3:
                last[k] = r['round']; continue
            last[k] = r['round']; eps[sp].append(r)
    res['retreat_rule'] = dict(rule=S_ret.report(held), combat_unacceptable=S_acc.report(held))
    res['retreat_tables'] = {sp: {'|'.join(k[:3]): dict(n=t[k], retreat=frac(t[k], t[k[:3] + ('retreat',)])) for k in t if k[3] == 'n'}
                             for sp, t in rt.items()}
    print(S_ret.line(held)); print(S_acc.line(held))
    rd = {}
    for sp, E in eps.items():
        n = len(E); o = dict(episodes=n)
        hw_short = away_home = closer_than_away = cheb_home = 0
        for r in E:
            d = r['y']['dir']; p0, e0, p3 = map(tuple, (d['p0'], d['e0'], d['p3']))
            if r['game'] not in homes:
                with gzip.open(Path(CACHE[r['cohort']]) / f"{r['game']}.json.gz") as f:
                    gm = json.load(f)
                homes[r['game']] = sorted(spawn(gm['map'], gm['side']))
            H = homes[r['game']]
            hd = lambda q: min(cheb(q, h) for h in H)
            vx, vy = p0[0] - e0[0], p0[1] - e0[1]; s = max(abs(vx), abs(vy), 1)
            away = (p0[0] + 3 * round(vx / s), p0[1] + 3 * round(vy / s))
            hw_short += d['dhw'] < 0; away_home += hd(away) < hd(p0); closer_than_away += hd(p3) < hd(away)
            cheb_home += hd(p3) < hd(p0)
        wa = [r['y']['dir'] for r in E if r['y']['dir']['dally'] is not None and r['y']['dir']['ally_d0'] >= 3]
        al = [r['y']['dir'] for r in E if r['y']['dir']['dalt'] is not None]
        o.update(home_walk_shorter=frac(n, hw_short), home_cheb_closer=frac(n, cheb_home), straight_away_placebo_home_closer=frac(n, away_home),
                 nearer_home_than_straight_away=frac(n, closer_than_away),
                 toward_nearest_ally=frac(len(wa), sum(q['dally'] < 0 for q in wa)), away_from_ally=frac(len(wa), sum(q['dally'] > 0 for q in wa)),
                 ally_n=len(wa), altar_nearer=frac(len(al), sum(q['dalt'] < 0 for q in al)), altar_farther=frac(len(al), sum(q['dalt'] > 0 for q in al)),
                 ends_in_bush=frac(n, sum(r['y']['dir']['bush'] for r in E)), started_in_bush=frac(n, sum(r['y']['dir']['bush0'] for r in E)))
        ends = collections.Counter(r['y']['end'][0] for r in E)
        o['ends'] = {k: frac(n, v) for k, v in ends.items()}
        farm = [r['y']['end'][2] for r in E if r['y']['end'][0] == 'farm' and r['y']['end'][2]['last'] is not None]
        o['farm_same_group'] = dict(n=len(farm), same=frac(len(farm), sum(f['same'] for f in farm)))
        tt = collections.defaultdict(list)
        for r in E:
            if r['y']['end'][1] is not None:
                tt[r['y']['end'][0]].append(r['y']['end'][1])
        o['median_turns'] = {k: sorted(v)[len(v) // 2] for k, v in tt.items()}
        for lo, hi in ((0, 0.3), (0.3, 0.6), (0.6, 1.01)):
            s = [r for r in E if lo <= r['x']['hpf'] < hi]
            o[f'ends_hp_{lo}-{hi}'] = dict(n=len(s), **{k: frac(len(s), v) for k, v in collections.Counter(r['y']['end'][0] for r in s).items()})
        rd[sp] = o
    rd['examples_held'] = [dict(game=r['game'], round=r['round'], actor=r['actor'], type=NAMES[r['type']], end=r['y']['end'][0])
                           for r in eps['held'][:12]]
    res['retreat_episodes'] = rd
    print('retreat dir', json.dumps({k: v for k, v in rd['held'].items() if not k.startswith('ends_hp')}))

    # ---- Section 4: convergence.
    cv = {}
    for sp in ('fit', 'held'):
        n, s, ar = C[sp]['conv_n'], C[sp]['conv_sum'], C[sp]['conv_arrive']
        cv[sp] = {'|'.join(map(str, k)): dict(n=n[k], mean_d5_change=round(s[k] / n[k], 3), arrive_within6=frac(n[k], ar[k])) for k in sorted(n)}
    res['convergence'] = cv

    # ---- Section 5: after a kill.
    S_kill = Score('after a kill: fights on iff another enemy is in sight')
    kt = collections.defaultdict(collections.Counter)
    for k in Ls['kills']:
        c, game, group, rnd, actor, typ, gems, hp, others, end = k
        r = dict(cohort=c, game=game, group=group, round=rnd, actor=actor, type=typ)
        S_kill.add(r, others > 0, end == 'fight', base=False)
        sp = role[c]
        gb = '0-9' if gems < 10 else '10-29' if gems < 30 else '30+'
        for key in ('all', f'gems {gb}', f"others {'>0' if others else '0'}", f"hp {'<0.4' if hp < 0.4 else '<0.64' if hp < 0.64 else '>=0.64'}"):
            kt[sp][(key, 'n')] += 1; kt[sp][(key, end)] += 1
    res['after_kill'] = dict(rule=S_kill.report(held), table={sp: {key: {e: frac(t[(key, 'n')], t[(key, e)]) for e in
                                                                        ('fight', 'farm', 'home', 'tribute', 'death', 'timeout')} | dict(n=t[(key, 'n')])
                                                                   for key in sorted({k for k, _ in t})} for sp, t in kt.items()})
    print(S_kill.line(held))

    # ---- Section 6: profiles.
    pr = {}
    for sp in ('fit', 'held'):
        pr[sp] = {}
        for k, v in C[sp].items():
            if k.startswith('profile:'):
                n = v['n']
                pr[sp][k[8:]] = dict(n=n, enemy_visible=frac(n, v['enemy_visible']), champ_hit=frac(n, v['champ_hit']),
                                     camp_hit=frac(n, v['camp_hit']), tribute_start=frac(n, v['tribute_start']),
                                     range_n=v['range_n'], range_close=frac(v['range_n'], v['range_close']),
                                     contact_n=v['contact_n'], contact_hit=frac(v['contact_n'], v['contact_hit']))
    res['profiles'] = pr
    write(a.out, res)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
