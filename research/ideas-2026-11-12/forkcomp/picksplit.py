"""Do SPSA score gradients differ by pick count (or opponent)? A test of per-composition constants on tune games.jsonl.

    python3 picksplit.py RUN [RUN...] [--split picks|opp] [--perm N] [--h 0.19] [--out OUT.json]

Each game of iteration k, sign pair p gives d = s_p - s_m with E[d] = sum_i 2 cn_i D_pi gamma_i(G), gamma_i(G) the
score gradient (scaled x) in the game's group G. Per constant, u = d D_pi is regressed on 2 cn_i [epoch dummies,
group dummies] (het.py's estimator, research/ideas-2026-11-05/oc5-tools), map-clustered SEs. The group slopes are
gradient differences from the base group; a constant whose optimum differs by group has a group slope well beyond
its SE, of opposite sign to the base gradient in one group. The null permutes group labels across maps (picks) or
across games' opponents within maps (opp). Prize: the debiased E[(W.z)^2] x 0.6 / (2h), the most a per-group constant
could gain at curvature h (an upper bound: research/EXPERIMENTS.md found such bounds ~4x optimistic).
"""
import argparse, json, math, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path('/home/ubuntu/cambc-autumn')
FEATS = Path('/home/ubuntu/tmp-offload/tune5/mc/features.json')


def picks_lookup():
    feats = json.load(open(FEATS))
    by_name = {}
    for k, v in feats.items():
        by_name.setdefault(Path(k).name, v['picks'])
    idx_cache = {}

    def get(m):
        if m in feats:
            return feats[m]['picks']
        p = (ROOT / m).resolve()
        d = p.parent
        if d not in idx_cache:
            idx_cache[d] = {}
            f = d / 'index.json'
            if f.exists():
                for x in json.load(open(f))['maps']:
                    idx_cache[d][x['file']] = x['metrics'].get('picks')
        v = idx_cache[d].get(p.name)
        if v is None:
            v = by_name.get(p.name)
        return v
    return get


def opp_family(o):
    o = o.lower()
    if 'flp' in o or o.endswith('-f') or o.endswith('-fl') or 'fish' in o:
        return 'fish'
    if 'mt3' in o or o.endswith('-m') or 'mite' in o:
        return 'mite'
    return 'other'


def load(run, split, epochs, pk):
    lines = [json.loads(l) for l in open(ROOT / 'replays/tune' / run / 'games.jsonl')]
    names = lines[0]['names']
    K = max(r['k'] for r in lines)
    I, E = len(names), epochs
    # unit = (map) for picks; (map, opponent family) for opp: clusters stay maps
    groups = ['4', '3', '5'] if split == 'picks' else ['other', 'fish', 'mite']
    b = defaultdict(lambda: np.zeros((E, I))); q = defaultdict(lambda: np.zeros((E, I))); n = defaultdict(lambda: np.zeros(E))
    missing = set()
    for r in lines:
        assert r['names'] == names
        e = min(E - 1, (r['k'] - 1) * E // K)
        cn = np.array(r['cn']); D = np.array(r['deltas'], dtype=float); sc = r['scores']
        for gi, (m, o, s) in enumerate(r['games']):
            if split == 'picks':
                v = pk(m)
                if v is None:
                    missing.add(m); continue
                g = str(v)
            else:
                g = opp_family(o)
            for p in range(len(D)):
                a, c = sc[f'p{p}'][gi], sc[f'm{p}'][gi]
                if a is None or c is None:
                    continue
                w = 2 * cn
                b[(m, g)][e] += w * (a - c) * D[p]
                q[(m, g)][e] += w * w
                n[(m, g)][e] += 1
    units = sorted(b)
    present = [g for g in groups if any(u[1] == g for u in units)]
    base = present[0]
    others = present[1:]
    maps = sorted({u[0] for u in units}); mi = {m: i for i, m in enumerate(maps)}
    B = np.stack([b[u] for u in units]); Q = np.stack([q[u] for u in units]); N = np.stack([n[u] for u in units])
    Z = np.array([[1.0 if u[1] == g else 0.0 for g in others] for u in units]).reshape(len(units), len(others))
    cl = np.array([mi[u[0]] for u in units])
    return names, units, B, Q, N, Z, cl, base, others, K, missing


def fit(B, Q, Z, cl, nclust):
    U, E, I = B.shape
    J = Z.shape[1]; P = E + J
    betas, covs = np.zeros((I, P)), np.zeros((I, P, P))
    for i in range(I):
        XtX = np.zeros((P, P)); Xtu = np.zeros(P)
        qi, bi = Q[:, :, i], B[:, :, i]
        for e in range(E):
            qe, be = qi[:, e], bi[:, e]
            XtX[e, e] += qe.sum(); XtX[e, E:] += qe @ Z; XtX[E:, e] += qe @ Z
            XtX[E:, E:] += (Z * qe[:, None]).T @ Z
            Xtu[e] += be.sum(); Xtu[E:] += be @ Z
        inv = np.linalg.pinv(XtX)
        beta = inv @ Xtu
        S = np.zeros((nclust, P))
        for e in range(E):
            res = bi[:, e] - qi[:, e] * (beta[e] + Z @ beta[E:])
            np.add.at(S[:, e], cl, res)
            np.add.at(S[:, E:], cl, res[:, None] * Z)
        betas[i] = beta; covs[i] = inv @ (S.T @ S) @ inv
    return betas, covs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('runs', nargs='+')
    ap.add_argument('--split', default='picks', choices=['picks', 'opp'])
    ap.add_argument('--epochs', type=int, default=4)
    ap.add_argument('--perm', type=int, default=500)
    ap.add_argument('--h', type=float, default=0.19)
    ap.add_argument('--out')
    a = ap.parse_args()
    pk = picks_lookup()
    report = {}
    for run in a.runs:
        names, units, B, Q, N, Z, cl, base, others, K, missing = load(run, a.split, a.epochs, pk)
        nclust = cl.max() + 1
        E, I, J = a.epochs, len(names), Z.shape[1]
        ng = {g: int(N[[i for i, u in enumerate(units) if u[1] == g]].sum()) for g in [base] + others}
        print(f'== {run}: {K} iterations, {int(N.sum())} paired games on {nclust} maps; groups {ng}; split {a.split}, base {base}'
              + (f'; {len(missing)} maps without picks' if missing else ''))
        betas, covs = fit(B, Q, Z, cl, nclust)
        W = betas[:, E:]
        se = np.sqrt(np.stack([np.diag(c)[E:] for c in covs]))
        t = W / se
        wald = np.array([float(W[i] @ np.linalg.solve(covs[i][E:, E:], W[i])) for i in range(I)])
        # main gradient (the base group's, epoch-averaged) and its SE
        g0 = betas[:, :E].mean(1)
        # group shares (games) for the prize
        wts = N.sum(1)
        Sz = np.cov(Z.T, aweights=wts).reshape(J, J)
        k = 0.6 / (2 * a.h) * 100

        def prize(bs, cs):
            out = []
            for i in range(I):
                Wi, C = bs[i, E:], cs[i][E:, E:]
                out.append(float(Wi @ Sz @ Wi) - float(np.trace(Sz @ C)))
            return np.array(out)
        pz = prize(betas, covs)
        rng = np.random.default_rng(1112)
        null_omni, null_prize, null_wald = [], [], []
        # permute group labels: for picks across maps (a map's units keep one label), for opp within map
        umaps = sorted(set(cl))
        for _ in range(a.perm):
            if a.split == 'picks':
                lab = Z.copy()
                # map -> its row label; permute the map labels
                first = {}
                for i, c in enumerate(cl):
                    first.setdefault(c, i)
                order = np.array([first[c] for c in umaps])
                perm = rng.permutation(order)
                remap = {c: perm[j] for j, c in enumerate(umaps)}
                lab = Z[[remap[c] for c in cl]]
            else:
                lab = Z.copy()
                for c in umaps:
                    idx = np.where(cl == c)[0]
                    lab[idx] = Z[rng.permutation(idx)]
            be, ce = fit(B, Q, lab, cl, nclust)
            tp = be[:, E:] / np.sqrt(np.stack([np.diag(c_)[E:] for c_ in ce]))
            null_omni.append(float((tp ** 2).sum()))
            null_wald.append([float(be[i, E:] @ np.linalg.solve(ce[i][E:, E:], be[i, E:])) for i in range(I)])
            null_prize.append(prize(be, ce).sum())
        null_omni = np.array(null_omni); null_wald = np.array(null_wald); null_prize = np.array(null_prize)
        omni = float((t ** 2).sum())
        p_omni = float((null_omni >= omni).mean())
        tot = pz.sum() * k
        print(f'omnibus sum t^2 {omni:.1f} (df {I * J}; null mean {null_omni.mean():.1f}, 95% {np.percentile(null_omni, 95):.1f}); perm p {p_omni:.3f}')
        print(f'prize of splitting every constant (debiased, h {a.h}): {tot:+.2f} points; null mean {null_prize.mean() * k:+.2f}, '
              f'95% {np.percentile(null_prize, 95) * k:+.2f}; perm p {float((null_prize >= pz.sum()).mean()):.3f}')
        print(f'{"constant":28s} {"g(" + base + ")":>8s} ' + ' '.join(f'{"d" + g:>14s}' for g in others) + '  wald p   flip?')
        rows = []
        for i, nm in enumerate(names):
            pw = float((null_wald[:, i] >= wald[i]).mean())
            cells = ' '.join(f'{W[i, j]:+.3f}({t[i, j]:+.1f})' for j in range(J))
            gse = math.sqrt(np.mean([covs[i][e, e] for e in range(E)]) / E)
            flips = [others[j] for j in range(J) if abs(t[i, j]) > 2 and abs(g0[i] / max(gse, 1e-9)) > 2 and np.sign(g0[i] + W[i, j]) != np.sign(g0[i])
                     and abs((g0[i] + W[i, j])) > 2 * se[i, j]]
            mark = 'FLIP ' + ','.join(flips) if flips else ''
            print(f'{nm:28s} {g0[i]:+8.3f} {cells}  {pw:6.3f}  {mark}')
            rows.append({'name': nm, 'g_base': float(g0[i]), 'W': W[i].tolist(), 'se': se[i].tolist(), 't': t[i].tolist(),
                         'wald': float(wald[i]), 'wald_p': pw, 'prize': float(pz[i] * k), 'flips': flips})
        report[run] = {'split': a.split, 'base': base, 'others': others, 'games': ng, 'maps': int(nclust), 'omni': omni,
                       'p_omni': p_omni, 'prize': tot, 'prize_null_mean': float(null_prize.mean() * k),
                       'prize_null_95': float(np.percentile(null_prize, 95) * k), 'rows': rows}
        print()
    if a.out:
        json.dump(report, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
