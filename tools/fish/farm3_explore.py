"""Structural hypothesis tests for Fish's camp destinations (FARM3.md section 4).

Each test fits on FIT (model, confirm, third, fourth) and scores HELD (fifth, sixth) on farm2's rows
against the farm2 logit refitted on FIT, unless stated. Writes OUT.json (refuses to overwrite).
  python3 tools/fish/farm3_explore.py OUT.json TEST [TEST...]
Tests:
  habit      per-map lookup: most frequent FIT label for (map, side, champion, reason, previous group)
  commit     allies' committed destinations (their own later labels: an oracle for shared claims)
  pairs      same-round co-deciders: does the later actor (turn order) follow or avoid the earlier
  payout     spawn trips: is the destination the one ranked first at the previous payout?
  closed     closed-form astraeus rate scores, constants grid-searched on FIT
  liveness   enemy/ally dead fractions and score lead (readable by Fish) as extra logit terms
  truth      observer-truth camp states instead of own memory (all groups; respawning only)
  unshared   observer truth only where no ally sighting is newer than own memory
  lag        team memory with ally sightings at least 10 / 40 rounds old
  opening    round-1 destinations: nearest, individual rate, greedy team assignment, one pack
  kinds      team memory from a subset of ally sightings: the ally on the group's tiles / off them,
             respawning states only / other states only
Observer data (truth, liveness, turn order) are diagnostics or Fish-readable facts as stated.
"""
import argparse
import bisect
import collections
import copy
import gzip
import itertools
import json
import math
from pathlib import Path

import numpy as np

import choice_model
from farm2_features import horizon, kill_rounds, own_strength, team_near
from farm3_common import ALIVE, ID, OBS, Game, load, team_rounds, write_json
from farm3_lib import (FIT, HELD, accuracy, argmax, bootstrap, candidates, cohort_paths, fit_farm2, rows_of, score_rows)
from farm3_memory import sightings


class Ctx:
    def __init__(self):
        self.fit = rows_of(FIT); self.held = rows_of(HELD)
        model, run = fit_farm2(self.fit)
        self.model, self.run = model, run
        self.fit_sc = score_rows(self.fit, model, run); self.held_sc = score_rows(self.held, model, run)
        self.base = [argmax(i, s) for i, s in self.held_sc]
        self.base_fit = [argmax(i, s) for i, s in self.fit_sc]

    def compare(self, pred, rows=None):
        rows = rows or self.held
        return dict(model=accuracy(rows, pred), farm2=accuracy(rows, self.base), boot_minus_farm2=bootstrap(rows, pred, self.base))

    def refit(self, F, H, extra=None):
        model, run = fit_farm2(F, extra=extra)
        pred = [argmax(i, s) for i, s in score_rows(H, model, run)]
        return model, self.compare(pred)


def prev_group(r):
    x = r['x']
    if x['reason'] == 'payout':
        return x['own_group']
    return next((c['id'] for c in x['candidates'] if c['last_group']), None)


def t_habit(C):
    levels = [lambda r: (r['map'], r['side'], r['x']['type'], r['x']['reason'], prev_group(r)),
              lambda r: (r['map'], r['side'], r['x']['reason'], prev_group(r)),
              lambda r: (r['map'], r['side'], r['x']['type'], r['x']['reason'])]
    out = {}
    for n, key in enumerate(levels):
        tab = collections.defaultdict(collections.Counter)
        for r in C.fit:
            tab[key(r)][r['y']['targets'][0]] += 1
        cov = hab = f2 = 0
        for r, p in zip(C.held, C.base):
            cnt = tab.get(key(r)); ids = [c['id'] for c in candidates(r['x'])]
            opts = [(v, -g) for g, v in (cnt or {}).items() if g in ids]
            if not opts:
                continue
            y = r['y']['targets'][0]; cov += 1; hab += -max(opts)[1] == y; f2 += p == y
        out[f'level{n}'] = dict(covered=cov, habit=hab, farm2=f2)
    return out


def orders():
    cache = {}

    def idx(g, rd, a):
        if g not in cache:
            cache[g] = team_rounds(g)
        T = cache[g]
        o = T.get(rd, {}).get('order', []) if T else []
        return o.index(a) if a in o else 99
    return idx


def t_commit(C):
    oidx = orders()
    com = collections.defaultdict(list)
    for r in C.fit + C.held:
        com[r['game']].append((r['round'], oidx(r['game'], r['round'], r['actor']), r['actor'], r['y']['targets'][0], r['y']['round'],
                               tuple(r['x']['me_xy'])))

    def extra(r, cs, far_only=False):
        t = r['round']; me = oidx(r['game'], t, r['actor']); act = {}
        for d, o, a, g, h, pos in com[r['game']]:
            if a != r['actor'] and (d, o) < (t, me) and h >= t and d >= t - 40 and (a not in act or act[a][0] < (d, o)):
                act[a] = ((d, o), g, d == t, pos)
        res = []
        for c in cs:
            far = sum(v[1] == c['id'] and max(abs(v[3][0] - r['x']['me_xy'][0]), abs(v[3][1] - r['x']['me_xy'][1])) > 8 for v in act.values())
            f = dict(com_far=float(far))
            if not far_only:
                f |= dict(com_n=float(sum(v[1] == c['id'] for v in act.values())), com_same=float(sum(v[1] == c['id'] and v[2] for v in act.values())))
            res.append(f)
        return res
    out = {}
    for name, ex in (('all', extra), ('far_only', lambda r, cs: extra(r, cs, True))):
        model, res = C.refit(C.fit, C.held, ex)
        res['weights'] = {k: {f: round(v, 3) for f, v in model['weights'][k].items() if f.startswith('com')} for k in model['weights']}
        out[name] = res
    return out


def t_pairs(C):
    oidx = orders()
    rows = C.fit + C.held; pred = C.base_fit + C.base
    by = collections.defaultdict(list)
    for k, r in enumerate(rows):
        by[r['game'], r['round']].append(k)
    st = collections.Counter()
    for (g, rd), ks in by.items():
        if len(ks) < 2:
            continue
        ks = sorted(ks, key=lambda k: oidx(g, rd, rows[k]['actor']))
        for i, j in itertools.combinations(range(len(ks)), 2):
            a, b = rows[ks[i]], rows[ks[j]]
            ya, yb = a['y']['targets'][0], b['y']['targets'][0]; pb = pred[ks[j]]
            rs = a['x']['reason'] + '/' + b['x']['reason']
            st[rs, 'pairs'] += 1; st[rs, 'same_label'] += ya == yb
            if pb == ya:
                st[rs, 'B_top_is_A_label'] += 1; st[rs, 'B_follows'] += yb == ya
            else:
                st[rs, 'B_top_not_A_label'] += 1; st[rs, 'B_matches_own_top'] += yb == pb; st[rs, 'B_picks_A_label'] += yb == ya
    return {' '.join(k): v for k, v in sorted(st.items())}


def t_payout(C):
    frozen = json.loads(Path('research/fish-2026-11-05/choice-fit.json').read_text())
    st = collections.Counter()
    for c in FIT + HELD:
        rows = [json.loads(l) for l in gzip.open(cohort_paths(c)['choice'], 'rt')]
        by = collections.defaultdict(list)
        for r in rows:
            by[r['game'], r['actor']].append(r)
        deaths = {}
        for (g, a), rs in by.items():
            rs.sort(key=lambda r: r['round'])
            if g not in deaths:
                deaths[g] = {R['r']: {ch[ID]: ch[12] for ch in R['ch']} for R in load(OBS / f'{g}.json.gz')['rounds']}
            D = deaths[g]
            for i, r in enumerate(rs):
                if r['x']['reason'] != 'spawn' or r['y']['status'] != 'hit':
                    continue
                prev = [p for p in rs[:i] if p['x']['reason'] == 'payout']
                if not prev or prev[-1]['y']['status'] != 'home':
                    continue
                p = prev[-1]
                if D.get(r['round'], {}).get(a) != D.get(p['round'], {}).get(a):
                    continue
                y = r['y']['targets'][0]; st['n'] += 1
                st['spawn_time_top1'] += choice_model.predict(r['x'], frozen) == y
                st['payout_time_top1'] += choice_model.predict(p['x'], frozen) == y
                st['label_is_paid_group'] += y == p['x']['own_group']
                for name, x in (('spawn_time_top2', r['x']), ('payout_time_top2', p['x'])):
                    sc = choice_model.scores(x, frozen)
                    st[name] += y in sorted(sc, key=lambda k: (-sc[k], k))[:2]
    return dict(st)


def prep_closed(rows):
    out = []
    for r in rows:
        x = r['x']; e = r['e']; S = own_strength(x); A = []
        for c in candidates(x):
            ce = e['candidates'][str(c['id'])]
            us, them = ce['from_us'], ce['from_them']
            share = min(1.0, 2 * them / max(1, us + them)) if us < 999 and them < 999 else 1.0
            A.append([c['id'], c['gems'], c['gold'], c['walk'], c['respawn'], kill_rounds(x, c, ce, S + team_near(x, e, c)[0]),
                      c['state'], share, horizon(e), float(c['ally_age'] is not None and c['ally_age'] <= 10)])
        out.append((np.array(A, dtype=float).reshape(-1, 10), r['y']['targets'][0], x['reason']))
    return out


def closed_score(gem=3, a=1.0, hz=1.0, sp=0.0, ep=0.0, up=0.0, rc=0.0):
    def f(A):
        worth = A[:, 1] * gem + A[:, 2]
        R = np.maximum(1, np.maximum(A[:, 3], A[:, 4]) + A[:, 5] + np.where(A[:, 6] == 2, 0, 7))
        return (np.log1p(worth) - a * np.log(R) - hz * np.log1p(R / A[:, 8]) + sp * np.log(np.maximum(A[:, 7], 0.05))
                - ep * (A[:, 6] == 2) - up * (A[:, 6] == 0) - rc * A[:, 9])
    return f


def closed_pred(P, f):
    out = []
    for A, y, rs in P:
        if not len(A):
            out.append(None); continue
        s = f(A); out.append(int(A[:, 0][s >= s.max() - 1e-9].min()))
    return out


def t_closed(C):
    PF, PH = prep_closed(C.fit), prep_closed(C.held)
    res = dict(astraeus_rate_gem3=C.compare(closed_pred(PH, closed_score())),
               astraeus_rate_gem10=C.compare(closed_pred(PH, closed_score(gem=10))))
    grid = list(itertools.product([1, 3, 5], [0.5, 1, 2, 3], [0, 1], [0, 1, 2, 3], [0, 1, 2], [0, 0.5, 1], [0, 0.5]))
    best = {}
    for reason in ('payout', 'spawn'):
        rows = [k for k, z in enumerate(PF) if z[2] == reason]
        sub = [PF[k] for k in rows]
        score = []
        for p in grid:
            pr = closed_pred(sub, closed_score(*p))
            score.append((sum(a == z[1] for a, z in zip(pr, sub)), p))
        best[reason] = max(score)
    pred = [None] * len(PH)
    for reason in ('payout', 'spawn'):
        ks = [k for k, z in enumerate(PH) if z[2] == reason]
        for k, v in zip(ks, closed_pred([PH[k] for k in ks], closed_score(*best[reason][1]))):
            pred[k] = v
    res['grid_best'] = dict(constants={k: dict(zip(['gem', 'a', 'hz', 'share', 'empty', 'unknown', 'recent'], v[1])) for k, v in best.items()},
                            fit_correct={k: v[0] for k, v in best.items()}, held=C.compare(pred))
    return res


def obs_cache():
    cache = {}

    def get(g):
        if g not in cache:
            cache.clear(); ob = load(OBS / f'{g}.json.gz'); cache[g] = (Game(ob), {R['r']: R for R in ob['rounds']})
        return cache[g]
    return get


def t_liveness(C):
    get = obs_cache()

    def extra(r, cs):
        G, R = get(r['game']); snap = R[r['round']]; ch = {c[ID]: c for c in snap['ch']}
        ed = sum(1 - ch[i][ALIVE] for i in G.enemy) / len(G.enemy); fd = sum(1 - ch[i][ALIVE] for i in G.fish) / len(G.fish)
        lead = snap['sub'][G.side] - snap['sub'][1 - G.side]
        return [dict(edead_enemyside=ed * (c['territory'] > 0), edead_terr=ed * max(0, c['territory']) / 10,
                     lead_enemyside=max(-1, min(1, lead / 300)) * (c['territory'] > 0), fdead_far=fd * min(c['walk'], 60) / 10) for c in cs]
    model, res = C.refit(C.fit, C.held, extra)
    res['weights'] = {k: {f: round(model['weights'][k][f], 3) for f in ('edead_enemyside', 'edead_terr', 'lead_enemyside', 'fdead_far')}
                      for k in model['weights']}
    return res


def truthify(rows, mode, get):
    out = []
    for r in rows:
        G, R = get(r['game']); snap = R[r['round']]; r2 = copy.deepcopy(r)
        for c in r2['x']['candidates']:
            sg = G.groups[c['id']]; st, _, _, resp = snap['gs'][sg['live']]
            if mode == 'respawn' and not (c['state'] == 3 or st == 3):
                continue
            c['state'] = st; c['respawn'] = max(0, resp) if st == 3 else 0; c['age'] = 0
            ce = r2['e']['candidates'][str(c['id'])]
            ce['hp_left'] = sum(snap['hp'][k] for k in sg['members']); ce['awake'] = sum(snap['aw'][k] and snap['hp'][k] > 0 for k in sg['members'])
        out.append(r2)
    return out


def t_truth(C):
    get = obs_cache()
    return {m: C.refit(truthify(C.fit, m, get), truthify(C.held, m, get))[1] for m in ('all', 'respawn')}


def shared_variant(rows, mode, lag, get):
    cur = None; out = []
    for r in rows:
        if r['game'] != cur:
            cur = r['game']; seen = sightings(Path(cohort_paths(r['cohort'])['raw']) / f'{cur}.json.gz')
        G, R = get(r['game']); snap = R[r['round']]; t = r['round']; r2 = copy.deepcopy(r)
        for c in r2['x']['candidates']:
            v = seen.get(c['id'], [])
            k = bisect.bisect_left(v, (r['step'],)) - 1
            while k >= 0 and (v[k][2] == r['actor'] or v[k][1] > t - lag):
                k -= 1
            own = t - c['age'] if c['age'] is not None else -1
            shared = k >= 0 and v[k][1] > own
            ce = r2['e']['candidates'][str(c['id'])]
            if mode == 'unshared' and not shared:
                sg = G.groups[c['id']]; st, _, _, resp = snap['gs'][sg['live']]
                c['state'] = st; c['respawn'] = max(0, resp) if st == 3 else 0; c['age'] = 0
                ce['hp_left'] = sum(snap['hp'][m] for m in sg['members'])
                ce['awake'] = sum(snap['aw'][m] and snap['hp'][m] > 0 for m in sg['members'])
            elif mode == 'lag' and shared:
                _, rd, _, q = v[k]
                if q[1] != c['state']:
                    ce['hp_left'] = sum([1350, 2400, 120, 120, 20000, 5000][x] for x in c['types']) if q[1] in (0, 1) else 0; ce['awake'] = 0
                c['state'] = q[1]; c['age'] = t - rd; c['respawn'] = max(0, q[4] - (t - rd)) if q[1] == 3 else 0
        out.append(r2)
    return out


def t_unshared(C):
    get = obs_cache()
    return C.refit(shared_variant(C.fit, 'unshared', 0, get), shared_variant(C.held, 'unshared', 0, get))[1]


def t_lag(C):
    get = obs_cache()
    return {lag: C.refit(shared_variant(C.fit, 'lag', lag, get), shared_variant(C.held, 'lag', lag, get))[1] for lag in (10, 40)}


FHP = {0: 1350, 1: 2400, 4: 20000, 5: 5000, 2: 120, 3: 120}


def t_opening(C=None):
    ops = {}
    for c in FIT + HELD:
        man = {e['sha256'][:16]: e for e in json.loads(Path(cohort_paths(c)['manifest']).read_text())}
        by = collections.defaultdict(list)
        for l in gzip.open(cohort_paths(c)['choice'], 'rt'):
            r = json.loads(l)
            if r['x']['reason'] == 'opening':
                by[r['game']].append(r)
        for g, rs in by.items():
            ops.setdefault((man[g]['map'], man[g]['side']), []).append((g, sorted(rs, key=lambda r: r['actor'])))
    same = pairs = 0
    for v in ops.values():
        for (_, a), (_, b) in itertools.combinations(v, 2):
            la = {r['x']['type']: tuple(r['y']['targets']) for r in a if r['y']['status'] == 'hit'}
            lb = {r['x']['type']: tuple(r['y']['targets']) for r in b if r['y']['status'] == 'hit'}
            for t in set(la) & set(lb):
                pairs += 1; same += la[t] == lb[t]
    data = []
    for k, v in sorted(ops.items()):
        g, rs = v[0]
        md = load(OBS / f'{g}.json.gz')['mapData']
        data.append((rs, 100 * max(1, max(md['width'], md['height']) / 50)))

    def cand(r):
        return [c for c in r['x']['candidates'] if c['walk'] < 999]

    def ev(pol):
        ok = n = 0
        for rs, H in data:
            for r, p in zip(rs, pol(rs, H)):
                if r['y']['status'] == 'hit':
                    n += 1; ok += p == r['y']['targets'][0]
        return dict(correct=ok, n=n, accuracy=ok / n)

    def greedy(split, crew):
        def pol(rs, H):
            n = collections.Counter(); st = collections.defaultdict(float); out = {}
            for r in rs:  # round 1: priority 0 everywhere, so id order
                S = r['x']['strength']; best = None
                for c in cand(r):
                    R = max(1, c['walk'] + sum(FHP[t] for t in c['types']) / (S + (st[c['id']] if crew else 0)) + 7)
                    v = math.log1p((3 * c['gems'] + c['gold']) / ((n[c['id']] + 1) if split else 1)) - math.log(R) - math.log1p(R / H)
                    if best is None or v > best[0] + 1e-12:
                        best = (v, c['id'])
                out[r['actor']] = best[1]; n[best[1]] += 1; st[best[1]] += S
            return [out[r['actor']] for r in rs]
        return pol

    def pack(rs, H):
        S = sum(r['x']['strength'] for r in rs)
        ids = set.intersection(*[{c['id'] for c in cand(r)} for r in rs])
        best = None
        for g in sorted(ids):
            cs = [next(c for c in cand(r) if c['id'] == g) for r in rs]
            R = max(1, min(x['walk'] for x in cs) + sum(FHP[t] for t in cs[0]['types']) / S + 7)
            v = math.log1p(3 * cs[0]['gems'] + cs[0]['gold']) - 2 * math.log(R) - math.log1p(R / H)
            if best is None or v > best[0]:
                best = (v, g)
        return [best[1]] * len(rs)
    one = collections.Counter()
    for rs, _ in data:
        ls = {r['y']['targets'][0] for r in rs if r['y']['status'] == 'hit'}
        if ls:
            one[len(ls)] += 1
    return dict(configs=len(data), determinism=dict(pairs=pairs, same_first_group=same), distinct_groups_per_opening=dict(one),
                nearest=ev(lambda rs, H: [min(cand(r), key=lambda c: (c['walk'], c['id']))['id'] for r in rs]),
                individual_rate=ev(greedy(False, False)), greedy_crew=ev(greedy(False, True)),
                greedy_split=ev(greedy(True, False)), greedy_split_crew=ev(greedy(True, True)), pack_rate=ev(pack))


def kind_sightings(raw):
    from breadth import static_groups, xy
    from decision_data import contexts
    g = json.loads(gzip.open(raw).read()); _, at = static_groups(g['map']); live = {}
    for t in g['turns']:
        for s in contexts(t):
            for c in s['camps']:
                live[c['group']] = at[xy(c)]
    seen = collections.defaultdict(list)
    for t in g['turns']:
        for s in contexts(t):
            me = xy(s['me']) if 'x' in s['me'] else None
            for q in s['groups']:
                if q[0] in live:
                    seen[live[q[0]]].append((t['step'], t['round'], t['id'], q, at.get(me) == live[q[0]]))
    for v in seen.values():
        v.sort(key=lambda z: (z[0], z[1]))
    return seen


def kind_variant(rows, keep):
    cur = None; out = []
    for r in rows:
        if r['game'] != cur:
            cur = r['game']; seen = kind_sightings(Path(cohort_paths(r['cohort'])['raw']) / f'{cur}.json.gz')
        t = r['round']; r2 = copy.deepcopy(r)
        for c in r2['x']['candidates']:
            v = seen.get(c['id'], []); k = bisect.bisect_left(v, (r['step'],)) - 1
            while k >= 0 and (v[k][2] == r['actor'] or not keep(v[k])):
                k -= 1
            if k < 0:
                continue
            _, rd, _, q, _ = v[k]; own = t - c['age'] if c['age'] is not None else -1
            if rd <= own:
                continue
            ce = r2['e']['candidates'][str(c['id'])]
            if q[1] != c['state']:
                ce['hp_left'] = sum([1350, 2400, 120, 120, 20000, 5000][x] for x in c['types']) if q[1] in (0, 1) else 0; ce['awake'] = 0
            c['state'] = q[1]; c['age'] = t - rd; c['respawn'] = max(0, q[4] - (t - rd)) if q[1] == 3 else 0
            if q[1] == 3:
                ce['respawn_raw'] = q[4]
        out.append(r2)
    return out


def t_kinds(C):
    keeps = dict(on_group_only=lambda z: z[4], off_group_only=lambda z: not z[4],
                 respawning_only=lambda z: z[3][1] == 3, not_respawning=lambda z: z[3][1] != 3)
    return {k: C.refit(kind_variant(C.fit, f), kind_variant(C.held, f))[1] for k, f in keeps.items()}


TESTS = dict(kinds=t_kinds, habit=t_habit, commit=t_commit, pairs=t_pairs, payout=t_payout, closed=t_closed, liveness=t_liveness,
             truth=t_truth, unshared=t_unshared, lag=t_lag, opening=t_opening)


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('out'); a.add_argument('tests', nargs='+', choices=sorted(TESTS))
    x = a.parse_args()
    if Path(x.out).exists():
        raise SystemExit(f'refusing to overwrite {x.out}')
    C = Ctx()
    res = dict(baseline_farm2_fit_on_FIT=accuracy(C.held, C.base))
    for t in x.tests:
        res[t] = TESTS[t](C)
        print(t, json.dumps(res[t])[:400], flush=True)
    write_json(x.out, res)


if __name__ == '__main__':
    main()
