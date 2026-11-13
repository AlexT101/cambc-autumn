"""Ladder seeding window: Monte Carlo of the top-4 ratings until the seeding snapshot.

Rating rule (fit_rating.py): Elo, scale 400, K = 32 per 5-game group with score = wins/5, both teams' pre-group
ratings. Each team plays one group per 10-minute tick. Matchmaking for the top 4 is resampled from the observed
ticks (which top-4 pairs met, and the rating of the outside opponent otherwise) in ranked games since 11-11 18:00Z.
Outside opponents keep their observed ratings.

Per run, uncertain inputs are drawn once: each top-4 team's performance rating against the rest (fitted, with its
standard error plus a version-drift term), and each top-4 head-to-head per-game rate (logit-normal around its point
estimate). The book changes only our rates against Fish (and Mite) from the time it goes live.

Usage: python3 seedsim.py MATCHES.csv [--runs N] [--out JSON]
"""
import argparse, csv, collections, itertools, json, math
from datetime import datetime, timezone
import numpy as np

TOP = ['US', 'FISH', 'MITE', 'CATS']
SHORT = {'547efb5b': 'US', '1890540d': 'FISH', 'ee83f5e5': 'MITE', '285f4eb5': 'CATS'}
# Ratings at 2026-11-13 00:30Z (ratings table).
START = {'US': 2912.8, 'FISH': 2908.3, 'MITE': 2856.4, 'CATS': 2751.8}
NOW = '2026-11-13T00:40:00Z'
LOCK = '2026-11-13T23:59:00Z'


def ts(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def load_ticks(path, since='2026-11-11T18'):
    seen, G = set(), collections.defaultdict(list)
    for r in csv.DictReader(open(path)):
        if r['match_id'] in seen or r['created_at'] < since:
            continue
        seen.add(r['match_id'])
        G[r['group_id']].append(r)
    ticks = collections.defaultdict(dict)
    for v in G.values():
        r = v[0]
        t = round(ts(r['created_at']) / 600)
        A, B = SHORT.get(r['team_a'][:8]), SHORT.get(r['team_b'][:8])
        if A:
            ticks[t][A] = (B if B else float(r['rating_b']))
        if B:
            ticks[t][B] = (A if A else float(r['rating_a']))
    full = [t for t in sorted(ticks) if len(ticks[t]) == 4]
    opp = np.full((len(full), 4), -1, np.int64)
    orat = np.zeros((len(full), 4))
    for k, t in enumerate(full):
        for i, T in enumerate(TOP):
            o = ticks[t][T]
            if isinstance(o, str):
                opp[k, i] = TOP.index(o)
            else:
                orat[k, i] = o
    return opp, orat


def run(opp, orat, n_runs, n_ticks, book_tick, rates, rng, perf, drift):
    """rates: dict pair -> (p_normal, p_book, logit_sd); returns final ratings (n_runs, 4)."""
    R = np.tile(np.array([START[t] for t in TOP]), (n_runs, 1))
    # per-run performance against the rest
    Pf = np.stack([rng.normal(perf[t][0], math.hypot(perf[t][1], drift), n_runs) for t in TOP], 1)
    # per-run head-to-heads (row index < column index), normal and book
    H = {}
    for (a, b), (pn, pb, sd) in rates.items():
        z = rng.normal(0, sd, n_runs)
        lg = lambda p: math.log(p / (1 - p))
        H[(TOP.index(a), TOP.index(b))] = (1 / (1 + np.exp(-(lg(pn) + z))), 1 / (1 + np.exp(-(lg(pb) + z))))
    ar = np.arange(n_runs)
    for step in range(n_ticks):
        k = rng.integers(0, len(opp), n_runs)
        o = opp[k]
        dR = np.zeros_like(R)
        for i in range(4):
            rest = o[:, i] < 0
            ro = orat[k, i]
            p = 1 / (1 + 10 ** ((ro - Pf[:, i]) / 400))
            w = rng.binomial(5, p)
            E = 1 / (1 + 10 ** ((ro - R[:, i]) / 400))
            dR[:, i] += np.where(rest, 32 * (w / 5 - E), 0)
        for (i, j), (pn, pb) in H.items():
            m = o[:, i] == j
            if not m.any():
                continue
            p = pb if step >= book_tick else pn
            w = rng.binomial(5, p)
            E = 1 / (1 + 10 ** ((R[:, j] - R[:, i]) / 400))
            d = 32 * (w / 5 - E)
            dR[:, i] += np.where(m, d, 0)
            dR[:, j] -= np.where(m, d, 0)
        R += dR
    return R


def orders(R):
    idx = np.argsort(-R, 1)
    keys = ['-'.join(TOP[i] for i in row) for row in idx]
    c = collections.Counter(keys)
    return {k: v / len(keys) for k, v in c.most_common()}


def partner_share(order_probs):
    out = collections.Counter()
    for k, v in order_probs.items():
        o = k.split('-')
        s = o.index('US')
        out[o[{0: 3, 3: 0, 1: 2, 2: 1}[s]]] += v
    return dict(out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('matches')
    ap.add_argument('--runs', type=int, default=20000)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--out')
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    opp, orat = load_ticks(a.matches)
    print('ticks in pool', len(opp), 'top-4 pair share per tick',
          {f'{TOP[i]}-{TOP[j]}': round(float(np.mean(opp[:, i] == j)), 3) for i, j in itertools.combinations(range(4), 2)})
    # Performance against the rest: ours since 11-11 18:00Z (v115-v118 era), others since Fish r8 (11-12 12:00Z).
    perf = {'US': (2899, 21), 'FISH': (2914, 32), 'MITE': (2908, 31), 'CATS': (2757, 26)}
    drift = 20  # versions changing before the lock
    window_ticks = round((ts(LOCK) - ts(NOW)) / 600)
    results = {}
    # Normal-play rates: 'scrim' = live pinned scrims (v118 vs Fish r8 57.4%, Mite 64.9%);
    # 'ranked' = our ranked results since Fish r8 (26/60 vs Fish, 31/55 vs Mite), the pessimistic case.
    scen = {'scrim': (0.57, 0.65), 'ranked': (0.45, 0.56)}
    for sc, (nf, nm) in scen.items():
        for interp, extra in (('lock', 0), ('lock+6h', 36)):
            for book_at in ('now', '12:00Z'):
                book_tick = 0 if book_at == 'now' else round((ts('2026-11-13T12:00:00Z') - ts(NOW)) / 600)
                for pf in ('off', 0.67, 0.75, 0.80, 0.88):
                    for pm in ('off', 0.75, 0.85):
                        bf = nf if pf == 'off' else pf
                        bm = nm if pm == 'off' else pm
                        rates = {('US', 'FISH'): (nf, bf, 0.15), ('US', 'MITE'): (nm, bm, 0.15),
                                 ('US', 'CATS'): (0.79, 0.79, 0.15), ('FISH', 'MITE'): (0.56, 0.56, 0.20),
                                 ('FISH', 'CATS'): (0.68, 0.68, 0.20), ('MITE', 'CATS'): (0.65, 0.65, 0.20)}
                        R = run(opp, orat, a.runs, window_ticks + extra, book_tick, rates, rng, perf, drift)
                        op = orders(R)
                        ps = partner_share(op)
                        key = f'{sc}|{interp}|book {book_at}|fish {pf}|mite {pm}'
                        results[key] = dict(normal=dict(fish=nf, mite=nm), book=dict(fish=bf, mite=bm), interp=interp,
                                            book_at=book_at, orders=op, partner=ps,
                                            us_seed1=float(np.mean(np.argmax(R, 1) == 0)),
                                            mean_rating={t: float(R[:, i].mean()) for i, t in enumerate(TOP)},
                                            fish_below_mite=float(np.mean(R[:, 1] < R[:, 2])),
                                            fish_below_cats=float(np.mean(R[:, 1] < R[:, 3])),
                                            mite_below_cats=float(np.mean(R[:, 2] < R[:, 3])))
                        r = results[key]
                        print(f"{key:48s} seed1 {r['us_seed1']:.3f}  partner CATS {ps.get('CATS', 0):.3f} FISH {ps.get('FISH', 0):.3f} "
                              f"MITE {ps.get('MITE', 0):.3f}  F<M {r['fish_below_mite']:.2f} F<C {r['fish_below_cats']:.4f} "
                              f"M<C {r['mite_below_cats']:.4f}  mean " + ' '.join(f'{t} {v:.0f}' for t, v in r['mean_rating'].items()))
    if a.out:
        json.dump(results, open(a.out, 'w'), indent=1)
