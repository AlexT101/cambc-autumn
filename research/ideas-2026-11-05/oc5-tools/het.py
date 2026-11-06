"""Map-conditioned gradient diagnostic from a tune run's games.jsonl (per-game scores; mapcond.md Stage 1).

    python3 het.py RUN [--perm N] [--out OUT.json]

Each game g of iteration k and sign pair p gives d = s_p - s_m, whose expectation is sum_i 2 cn_i D_pi gamma_i(z_g),
gamma_i the score gradient in scaled x at the map's features z. Per constant i, u = d D_pi is regressed on
2 cn_i [epoch dummies, z] (z standardised over the games), so the slopes W_ij are the gradient's change per SD of
feature j. Sums per (map, epoch) are sufficient, so the map-cluster SEs and the map-permutation null are exact and
cheap. Also: each half of the run, and a debiased prize bound W' S W 0.6 / (2 h).
"""
import argparse, json, math, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path('/home/ubuntu/cambc-autumn')
FEATS = ['log_area', 'picks', 'sym_rot', 'sym_vert', 'spawn_dist', 'camp_density', 'log_gems', 'log_gold', 'big_share',
         'contested', 'altars', 'bushes']


def load(run, feats, epochs, kmax=None):
    lines = [json.loads(l) for l in open(ROOT / 'replays/tune' / run / 'games.jsonl')]
    if kmax:
        lines = [r for r in lines if r['k'] <= kmax]
    names = lines[0]['names']
    K = max(r['k'] for r in lines)
    maps = sorted({g[0] for r in lines for g in r['games']})
    mi = {m: i for i, m in enumerate(maps)}
    I, E, M = len(names), epochs, len(maps)
    b = np.zeros((M, E, I)); q = np.zeros((M, E, I)); n = np.zeros((M, E))
    # Halves for the sign check: (half, map, epoch-of-half) sums, epoch = half.
    bh = np.zeros((2, M, I)); qh = np.zeros((2, M, I))
    opp_b = defaultdict(lambda: np.zeros(I)); opp_q = defaultdict(lambda: np.zeros(I))
    for r in lines:
        assert r['names'] == names
        e = min(E - 1, (r['k'] - 1) * E // K)
        h = 0 if r['k'] <= K // 2 else 1
        cn = np.array(r['cn'])
        D = np.array(r['deltas'], dtype=float)  # pairs x I
        sc = r['scores']
        for gi, (m, o, s) in enumerate(r['games']):
            j = mi[m]
            for p in range(len(D)):
                a, c = sc[f'p{p}'][gi], sc[f'm{p}'][gi]
                if a is None or c is None:
                    continue
                d = a - c
                w = 2 * cn
                b[j, e] += w * d * D[p]
                q[j, e] += w * w
                n[j, e] += 1
                bh[h, j] += w * d * D[p]
                qh[h, j] += w * w
                opp_b[o] += w * d * D[p]
                opp_q[o] += w * w
    Z = np.array([[feats[m][f] for f in FEATS] for m in maps], dtype=float)
    return names, maps, b, q, n, bh, qh, Z, K, dict(opp_b), dict(opp_q)


def fit(b, q, Z):
    """Per constant: WLS of u on [epoch dummies, z] from (map, epoch) sums. Returns beta (I x (E+J)), cluster cov."""
    M, E, I = b.shape
    J = Z.shape[1]
    P = E + J
    betas, covs = np.zeros((I, P)), np.zeros((I, P, P))
    # x_me = [onehot(e), z_m]
    for i in range(I):
        XtX = np.zeros((P, P)); Xtu = np.zeros(P)
        qi, bi = q[:, :, i], b[:, :, i]
        for e in range(E):
            qe, be = qi[:, e], bi[:, e]
            XtX[e, e] += qe.sum()
            XtX[e, E:] += qe @ Z
            XtX[E:, e] += qe @ Z
            XtX[E:, E:] += (Z * qe[:, None]).T @ Z
            Xtu[e] += be.sum()
            Xtu[E:] += be @ Z
        inv = np.linalg.inv(XtX)
        beta = inv @ Xtu
        # Map-cluster scores: sum_e x_me (b_me - q_me x_me' beta)
        S = np.zeros((M, P))
        for e in range(E):
            fitted = beta[e] + Z @ beta[E:]
            res = bi[:, e] - qi[:, e] * fitted
            S[:, e] += res
            S[:, E:] += res[:, None] * Z
        meat = S.T @ S
        betas[i] = beta
        covs[i] = inv @ meat @ inv
    return betas, covs


def tstats(betas, covs, E):
    W = betas[:, E:]
    se = np.sqrt(np.stack([np.diag(c)[E:] for c in covs]))
    return W, se, W / se


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('--feats', default='/home/ubuntu/tmp-offload/tune5/mc/features.json')
    ap.add_argument('--epochs', type=int, default=4)
    ap.add_argument('--perm', type=int, default=200)
    ap.add_argument('--h', type=float, default=0.19, help='score curvature per scaled unit^2 (mapcond.md: 0.19 from oc2)')
    ap.add_argument('--kmax', type=int)
    ap.add_argument('--out')
    a = ap.parse_args()
    feats = json.load(open(a.feats))
    names, maps, b, q, n, bh, qh, Z0, K, ob, oq = load(a.run, feats, a.epochs, a.kmax)
    # Standardise over games (map weights = rows per map).
    wm = n.sum(1)
    mu = (Z0 * wm[:, None]).sum(0) / wm.sum()
    sd = np.sqrt(((Z0 - mu) ** 2 * wm[:, None]).sum(0) / wm.sum())
    Z = (Z0 - mu) / sd
    E, I, J = a.epochs, len(names), len(FEATS)
    print(f'{a.run}: {K} iterations, {int(n.sum())} paired games, {len(maps)} maps, {I} constants x {J} features')
    betas, covs = fit(b, q, Z)
    W, se, t = tstats(betas, covs, E)
    g = betas[:, :E]
    gse = np.sqrt(np.stack([np.diag(c)[:E] for c in covs]))
    omni = float((t ** 2).sum())
    # Joint Wald per constant over its J slopes.
    wald = [float(W[i] @ np.linalg.solve(covs[i][E:, E:], W[i])) for i in range(I)]
    # Halves: fit each half with one epoch.
    th = []
    for h in range(2):
        bb, qq = bh[h][:, None, :], qh[h][:, None, :]
        be, ce = fit(bb, qq, Z)
        th.append(tstats(be, ce, 1))
    S = np.cov(Z.T, aweights=wm)

    def prize_of(betas, covs):
        out = []
        for i in range(I):
            W_, C = betas[i, E:], covs[i][E:, E:]
            out.append((float(W_ @ S @ W_) - float(np.trace(S @ C)),
                        math.sqrt(2 * float(np.trace(S @ C @ S @ C)) + 4 * float(W_ @ S @ C @ S @ W_))))
        return out
    # Permutation null over maps.
    rng = np.random.default_rng(546)
    null_omni, null_max, null_wald, null_prize = [], [], [], []
    for _ in range(a.perm):
        pz = Z[rng.permutation(len(Z))]
        be, ce = fit(b, q, pz)
        _, _, tp = tstats(be, ce, E)
        null_omni.append(float((tp ** 2).sum()))
        null_max.append(float(np.abs(tp).max()))
        null_wald.append([float(be[i, E:] @ np.linalg.solve(ce[i][E:, E:], be[i, E:])) for i in range(I)])
        null_prize.append([x for x, _ in prize_of(be, ce)])
    null_omni, null_max, null_wald = np.array(null_omni), np.array(null_max), np.array(null_wald)
    p_omni = float((null_omni >= omni).mean()) if a.perm else float('nan')
    # Prize: per constant, the debiased E_z[(W.z)^2] = W' S W - tr(S Cov(W)), S the games' feature covariance (here
    # the correlation, z standardised); a feature-conditioned value gains that x 0.6 (win per score) / (2 h), in win.
    prize = prize_of(betas, covs)
    null_prize = np.array(null_prize) if a.perm else np.zeros((1, I))
    tot = sum(p for p, _ in prize); tot_se = math.sqrt(sum(s * s for _, s in prize))
    k = 0.6 / (2 * a.h) * 100  # points of win rate per unit of E[(W z)^2]
    print(f'omnibus sum t^2 {omni:.1f} (df {I * J}; null mean {null_omni.mean() if a.perm else 0:.1f}, '
          f'95% {np.percentile(null_omni, 95) if a.perm else 0:.1f}, 99% {np.percentile(null_omni, 99) if a.perm else 0:.1f}), perm p {p_omni:.3f}')
    print(f'|t|>2: {int((np.abs(t) > 2).sum())}, |t|>3: {int((np.abs(t) > 3).sum())}, max |t| {np.abs(t).max():.2f} '
          f'(null 95% {np.percentile(null_max, 95) if a.perm else 0:.2f}); Bonferroni 0.05 over {I * J}: |t| > {bonf(I * J):.2f}')
    npt = null_prize.sum(1) * k
    print(f'prize (debiased, all constants): {tot * k:+.2f} +- {tot_se * k:.2f} points of win rate at h {a.h}; '
          f'permutation null mean {npt.mean():+.2f}, 95% {np.percentile(npt, 95):+.2f}, 99% {np.percentile(npt, 99):+.2f}, p {float((npt >= tot * k).mean()):.3f}')
    print('  excess over the null mean, per constant: ' + ', '.join(f'{nm} {(prize[i][0] - null_prize[:, i].mean()) * k:+.2f}' for i, nm in enumerate(names) if (prize[i][0] - null_prize[:, i].mean()) * k > 0.1))
    print()
    print(f'{"constant":24s} {"g(ep1..)":>30s}  wald(p)   strongest slopes (t; t in halves 1/2)')
    rows = []
    for i, nm in enumerate(names):
        pw = float((null_wald[:, i] >= wald[i]).mean()) if a.perm else float('nan')
        order = np.argsort(-np.abs(t[i]))[:3]
        sl = ', '.join(f'{FEATS[j]} {W[i, j]:+.3f} ({t[i, j]:+.1f}; {th[0][2][i, j]:+.1f}/{th[1][2][i, j]:+.1f})' for j in order)
        gs = ' '.join(f'{g[i, e]:+.3f}' for e in range(E))
        print(f'{nm:24s} {gs:>30s}  {wald[i]:5.1f}({pw:.2f})  {sl}   prize {prize[i][0] * k:+.2f}+-{prize[i][1] * k:.2f}')
        rows.append({'name': nm, 'g': g[i].tolist(), 'g_se': gse[i].tolist(), 'W': W[i].tolist(), 'se': se[i].tolist(),
                     't': t[i].tolist(), 't_h1': th[0][2][i].tolist(), 't_h2': th[1][2][i].tolist(), 'wald': wald[i],
                     'wald_p': pw, 'prize': prize[i][0] * k, 'prize_se': prize[i][1] * k})
    print()
    print('per opponent main gradient (scaled x, all iterations pooled):')
    for o in sorted(ob):
        gg = ob[o] / oq[o]
        print(f'  {o}: ' + ' '.join(f'{nm[:10]} {x:+.3f}' for nm, x in zip(names, gg)))
    if a.out:
        json.dump({'run': a.run, 'K': K, 'feats': FEATS, 'mu': mu.tolist(), 'sd': sd.tolist(), 'omni': omni,
                   'null_omni': null_omni.tolist(), 'null_max': null_max.tolist(), 'p_omni': p_omni, 'prize_total': tot * k,
                   'prize_total_se': tot_se * k, 'rows': rows}, open(a.out, 'w'))


def bonf(m):
    from statistics import NormalDist
    return NormalDist().inv_cdf(1 - 0.025 / m)


if __name__ == '__main__':
    main()
