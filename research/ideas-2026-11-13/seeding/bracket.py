"""Monte Carlo of the final: 16-team double elimination, best-of-21 series, seeded by ladder rank.

Bracket (assumed standard): WB round 1 pairs seeds 1-16, 8-9, 5-12, 4-13, 6-11, 3-14, 7-10, 2-15, so seeds 1 and 4
share a half and meet in the WB semi, as do 2 and 3. LB: WB R1 losers pair in order; WB R2 losers drop in reverse
order; WB semi losers drop crossed; LB final against the WB final loser. Grand final with a bracket reset (true
double elimination) unless --no-reset.

Per-game win rates carry uncertainty that is shared by every series between the same two teams in one event:
logit p = logit p_hat + scale * t_nu, with scale chosen so the bulk matches a normal of SD s (fatter tails beyond).
s combines the sampling error of p_hat with a systematic term (opponents updating before the lock, fresh maps vs
ladder maps, live vs local). Series odds then follow exactly from the binomial (first to 11 of 21).
"""
import argparse, itertools, json
import numpy as np
from scipy import stats

TOP = ['US', 'FISH', 'MITE', 'CATS']
# Finalists below the top 4, in current ladder order (seeds 5-16), with ratings at 2026-11-13 00:36Z.
REST = [('Claudus Maximus', 2641.2), ('NEETCoders', 2631.0), ('test4', 2628.1), ('Trzy Kwaterki', 2620.7),
        ('Sponge', 2492.9), ('Nyx', 2485.8), ('bentheboss', 2473.9), ('QS2isLaw', 2453.6),
        ('Team Kungarna', 2418.5), ('Rogue Lock Pickers', 2409.6), ('VeryGood', 2329.6), ('smurphy', 2275.3)]


def series_table(games=21, grid=20001):
    need = games // 2 + 1
    p = np.linspace(0, 1, grid)
    return p, stats.binom.sf(need - 1, games, p)


def logit(p):
    return np.log(p / (1 - p))


def build_prior(h2h, perf_rest, s_sys):
    """Return names, p_hat (16x16, row beats column) and s (16x16) for top-4 + rest."""
    names = TOP + [n for n, _ in REST]
    n = len(names)
    P = np.full((n, n), 0.5)
    S = np.zeros((n, n))
    rr = {nm: r for nm, r in REST}
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i >= j:
                continue
            if a in TOP and b in TOP:
                p, neff = h2h[(a, b)]
                ss = s_sys['top']
            elif a in TOP:
                # top-4 team vs a finalist from seed 5+: Elo from its fitted performance rating against the rest
                p = 1 / (1 + 10 ** ((rr[b] - perf_rest[a]) / 400))
                neff, ss = 150, s_sys['rest']
            else:
                p = 1 / (1 + 10 ** ((rr[b] - rr[a]) / 400))
                neff, ss = 150, s_sys['rest']
            s = np.sqrt(1 / (neff * p * (1 - p)) + ss ** 2)
            P[i, j], P[j, i] = p, 1 - p
            S[i, j] = S[j, i] = s
    return names, P, S


WB1 = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]


# Where WB losers land in the LB. Key: LB round 2 placement of the four WB R2 losers (index = LB R1 winner slot);
# LB round 4 placement of the two WB semi losers.
DROP2 = {'straight': [0, 1, 2, 3], 'reversed': [3, 2, 1, 0], 'halfswap': [2, 3, 0, 1]}
DROP4 = {'straight': [0, 1], 'crossed': [1, 0]}


def simulate(order, P_hat, S, n_events, nu, rng, reset=True, chunk=50000, drops=('reversed', 'crossed')):
    """order: list of team indices by seed (seed 1 first). Returns each team's share of titles."""
    d2, d4 = DROP2[drops[0]], DROP4[drops[1]]
    n = P_hat.shape[0]
    grid_p, grid_s = series_table()
    champs = np.zeros(n)
    t_scale = stats.norm.ppf(0.75) / stats.t.ppf(0.75, nu)
    iu = np.triu_indices(n, 1)
    L = logit(P_hat[iu])
    Ss = S[iu]
    seed_team = np.array(order)
    done = 0
    while done < n_events:
        m = min(chunk, n_events - done)
        done += m
        z = stats.t.rvs(nu, size=(m, len(L)), random_state=rng) * t_scale
        p = 1 / (1 + np.exp(-(L + Ss * z)))
        # series win probability of row team over column team
        sp = np.interp(p, grid_p, grid_s)
        SP = np.zeros((m, n, n), np.float32)
        SP[:, iu[0], iu[1]] = sp
        SP[:, iu[1], iu[0]] = 1 - sp
        ar = np.arange(m)

        def play(a, b):
            u = rng.random(m)
            aw = u < SP[ar, a, b]
            return np.where(aw, a, b), np.where(aw, b, a)

        T = lambda s: np.full(m, seed_team[s - 1])
        w1, l1 = zip(*[play(T(a), T(b)) for a, b in WB1])
        w2, l2 = zip(*[play(w1[2 * k], w1[2 * k + 1]) for k in range(4)])
        w3, l3 = zip(*[play(w2[2 * k], w2[2 * k + 1]) for k in range(2)])
        wbc, wbl = play(w3[0], w3[1])
        # LB
        lb1 = [play(l1[2 * k], l1[2 * k + 1])[0] for k in range(4)]
        lb2 = [play(lb1[k], l2[d2[k]])[0] for k in range(4)]
        lb3 = [play(lb2[2 * k], lb2[2 * k + 1])[0] for k in range(2)]
        lb4 = [play(lb3[k], l3[d4[k]])[0] for k in range(2)]
        lb5 = play(lb4[0], lb4[1])[0]
        lbc = play(lb5, wbl)[0]
        g1w, _ = play(wbc, lbc)
        if reset:
            g2w, _ = play(wbc, lbc)
            champ = np.where(g1w == wbc, wbc, g2w)
        else:
            champ = g1w
        champs += np.bincount(champ, minlength=n)
    return champs / n_events


def default_inputs(us_fish=0.57, us_mite=0.65):
    # Per-game win rate of the first team, with an effective sample size for its sampling error.
    h2h = {('US', 'FISH'): (us_fish, 340), ('US', 'MITE'): (us_mite, 345), ('US', 'CATS'): (0.79, 345),
           ('FISH', 'MITE'): (0.56, 300), ('FISH', 'CATS'): (0.68, 200), ('MITE', 'CATS'): (0.65, 400)}
    perf_rest = {'US': 2920, 'FISH': 2900, 'MITE': 2870, 'CATS': 2780}
    s_sys = {'top': 0.30, 'rest': 0.40}
    return h2h, perf_rest, s_sys


def partner_of_us(order_names):
    s = order_names.index('US')
    return order_names[{0: 3, 3: 0, 1: 2, 2: 1}[s]]


REP = {'CATS': ['US', 'FISH', 'MITE', 'CATS'], 'FISH': ['MITE', 'US', 'FISH', 'CATS'],
       'MITE': ['FISH', 'US', 'MITE', 'CATS']}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', type=int, default=200000)
    ap.add_argument('--nu', type=float, default=4, help='t degrees of freedom; 0 = normal')
    ap.add_argument('--s-top', type=float, default=0.30)
    ap.add_argument('--s-rest', type=float, default=0.40)
    ap.add_argument('--us-fish', type=float, default=0.57)
    ap.add_argument('--us-mite', type=float, default=0.65)
    ap.add_argument('--fish-mite', type=float, default=0.56)
    ap.add_argument('--no-reset', action='store_true')
    ap.add_argument('--drops', default='reversed,crossed', help='LB R2 drop (straight|reversed|halfswap),LB R4 drop (straight|crossed)')
    ap.add_argument('--orders', choices=['all', 'rep'], default='rep')
    ap.add_argument('--sanity', action='store_true')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--out')
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    nu = a.nu if a.nu > 0 else 1e9
    if a.sanity:
        n = 16
        P = np.full((n, n), 0.5); S = np.zeros((n, n))
        pr = simulate(list(range(n)), P, S, 100000, nu, rng)
        print('all 0.5: champion share min/max', pr.min().round(4), pr.max().round(4))
        P = np.triu(np.full((n, n), 0.999), 1) + np.tril(np.full((n, n), 0.001), -1); np.fill_diagonal(P, 0.5)
        pr = simulate(list(range(n)), P, S, 20000, nu, rng)
        print('strict order: seed-1 share', pr[0].round(4))
        raise SystemExit
    h2h, perf, s_sys = default_inputs(a.us_fish, a.us_mite)
    h2h[('FISH', 'MITE')] = (a.fish_mite, 300)
    s_sys = {'top': a.s_top, 'rest': a.s_rest}
    names, P, S = build_prior(h2h, perf, s_sys)
    res = {}
    perms = list(itertools.permutations(TOP)) if a.orders == 'all' else list(REP.values())
    for perm in perms:
        order = [TOP.index(t) for t in perm] + list(range(4, 16))
        pr = simulate(order, P, S, a.events, nu, rng, reset=not a.no_reset, drops=tuple(a.drops.split(',')))
        key = '-'.join(perm)
        res[key] = {names[i]: float(pr[i]) for i in range(16)}
        print(f'{key:22s} partner {partner_of_us(list(perm)):5s} US {pr[0]:.4f}  FISH {pr[1]:.4f}  MITE {pr[2]:.4f}  CATS {pr[3]:.4f}  rest {pr[4:].sum():.4f}')
    if a.out:
        json.dump(dict(params=vars(a), event_win=res), open(a.out, 'w'), indent=1)
