"""Per-opponent residuals of draft18's model on its own lab games (load.py's games.npz).

For the Fish (or Mite) body's games: logit(charybdis wins) = the deployed model's logit + extra terms on OUR team,
fitted by ridge logistic with the model's logit as a fixed offset:
  u   our champion (12, pooled over pick counts)          up  our champion x pick count (36)
  c   our champion x their champion (144)                 w   our champion x the first KW map features (12 x KW)
    py fit.py cv      5 map folds: held-out log loss (1e-4) of each block set and penalty against the offset alone
    py fit.py fit     the chosen fits on all games -> work/resid.json
"""
import json, os, sys, numpy as np
W = os.path.expanduser('~/tmp-offload/chynudge/work'); NC = 12; KW = 25
CH = ['ryth', 'vesper_vale', 'vendetta', 'cassi_and_issac', 'stellar', 'prism', 'marcella', 'willow', 'ren', 'varg', 'tavi', 'heart_of_ruin']
BOT = {'fish': 2, 'mite': 3, 'ocean': 1}
bits = lambda mask: ((mask[:, None] >> np.arange(NC)) & 1).astype(np.float32)

def rows(G, o):
    """The games of charybdis against bot o, from charybdis's side: ours, theirs (indicators), picks, map, win, offset."""
    a = (G['botB'] == o) & (G['botA'] == 0); b = (G['botA'] == o) & (G['botB'] == 0)
    ours = np.concatenate([G['A'][a], G['B'][b]]); theirs = np.concatenate([G['B'][a], G['A'][b]])
    return dict(ours=bits(ours), theirs=bits(theirs), picks=np.concatenate([G['picks'][a], G['picks'][b]]), key=np.concatenate([G['key'][a], G['key'][b]]),
                y=np.concatenate([G['win'][a], 1 - G['win'][b]]).astype(float), off=np.concatenate([G['eta'][a], -G['eta'][b]]),
                src=np.concatenate([G['srcB'][a], G['srcA'][b]]))
def design(R, Z, blocks):
    X = [np.ones((len(R['y']), 1), np.float32)]; pen = [0.0]; names = ['1']
    for blk, lam in blocks.items():
        if blk == 'u': X.append(R['ours']); n = NC
        elif blk == 'up': X.append(np.hstack([R['ours'] * (R['picks'] == p)[:, None] for p in (3, 4, 5)])); n = 3 * NC
        elif blk == 'c': X.append((R['ours'][:, :, None] * R['theirs'][:, None, :]).reshape(len(R['y']), -1)); n = NC * NC
        elif blk == 'w': X.append((R['ours'][:, :, None] * Z[R['key']][:, None, :KW].astype(np.float32)).reshape(len(R['y']), -1)); n = NC * KW
        pen += [lam] * n; names += [f'{blk}{i}' for i in range(n)]
    return np.hstack(X), np.array(pen), names
def newton(X, y, off, pen, iters=30):
    b = np.zeros(X.shape[1]); X64 = X.astype(np.float64)
    for _ in range(iters):
        pr = 1 / (1 + np.exp(-(off + X64 @ b))); g = X64.T @ (pr - y) + pen * b
        H = (X64 * (pr * (1 - pr))[:, None]).T @ X64 + np.diag(pen + 1e-8)
        step = np.linalg.solve(H, g); b -= step
        if np.abs(step).max() < 1e-8: break
    return b
def loss(X, y, off, b):
    e = off + X.astype(np.float64) @ b
    return float(np.mean(np.logaddexp(0, e) - y * e))

SETS = {  # block -> ridge penalty
    'u64': {'u': 64}, 'u16': {'u': 16}, 'u256': {'u': 256},
    'u+up': {'u': 16, 'up': 256}, 'u+up64': {'u': 16, 'up': 64},
    'u+c256': {'u': 16, 'c': 256}, 'u+c1024': {'u': 16, 'c': 1024}, 'u+c64': {'u': 16, 'c': 64},
    'u+w1024': {'u': 16, 'w': 1024}, 'u+w256': {'u': 16, 'w': 256}, 'u+w4096': {'u': 16, 'w': 4096},
}
def cv(G):
    Z = G['Z']; fold = np.arange(len(Z)) * 2654435761 % 5
    for name, o in BOT.items():
        R = rows(G, o); f = fold[R['key']]; print(f'\n{name}: {len(R["y"])} games, charybdis wins {R["y"].mean():.4f}; offset-only loss {loss(np.zeros((len(R["y"]), 1)), R["y"], R["off"], np.zeros(1)):.5f}', flush=True)
        for sn, blocks in SETS.items():
            X, pen, _ = design(R, Z, blocks); d = []
            for k in range(5):
                tr, te = f != k, f == k; b = newton(X[tr], R['y'][tr], R['off'][tr], pen)
                d.append(1e4 * (loss(X[te], R['y'][te], R['off'][te], b) - loss(X[te][:, :1], R['y'][te], R['off'][te], newton(X[tr][:, :1], R['y'][tr], R['off'][tr], pen[:1]))))
            print(f'  {sn:10s} held-out loss change {np.mean(d):+7.2f} (1e-4)  folds {" ".join(f"{x:+.1f}" for x in d)}', flush=True)
def fit(G, spec):
    Z = G['Z']; out = {}
    for name, o in BOT.items():
        R = rows(G, o); X, pen, names = design(R, Z, spec); b = newton(X, R['y'], R['off'], pen)
        pr = 1 / (1 + np.exp(-(R['off'] + X.astype(np.float64) @ b))); Hinv = np.linalg.inv((X.astype(np.float64) * (pr * (1 - pr))[:, None]).T @ X.astype(np.float64) + np.diag(pen + 1e-8))
        se = np.sqrt(np.diag(Hinv)); i = 1; res = {'games': len(R['y']), 'intercept': b[0], 'win': float(R['y'].mean()), 'model_win': float((1 / (1 + np.exp(-R['off']))).mean())}
        for blk in spec:
            n = {'u': NC, 'up': 3 * NC, 'c': NC * NC, 'w': NC * KW}[blk]; res[blk] = b[i:i + n].tolist(); res[blk + '_se'] = se[i:i + n].tolist(); i += n
        out[name] = res
        u = np.array(res['u']); us = np.array(res['u_se']); u0 = u - u.mean()
        print(f'\n{name}: our champion against this body, logit beyond the model (centred; se):')
        print('  ' + '  '.join(f'{CH[c][:6]} {u0[c]:+.3f} ({us[c]:.3f})' for c in np.argsort(-u0)))
        if 'c' in res:
            C = np.array(res['c']).reshape(NC, NC); Cs = np.array(res['c_se']).reshape(NC, NC); top = np.dstack(np.unravel_index(np.argsort(-np.abs(C / Cs).ravel())[:10], C.shape))[0]
            print('  largest our x their terms: ' + ', '.join(f'{CH[a][:5]}>{CH[b][:5]} {C[a, b]:+.3f} (z {C[a, b] / Cs[a, b]:+.1f})' for a, b in top))
    json.dump({'spec': spec, **out}, open(f'{W}/resid.json', 'w'))

if __name__ == '__main__':
    G = np.load(f'{W}/games.npz')
    if sys.argv[1] == 'cv': cv(G)
    else: fit(G, json.loads(sys.argv[2]) if len(sys.argv) > 2 else {'u': 16, 'c': 256})
