"""Within-(map,side) cell comparison of first-emblem family on later team gold / win, for one team's champion type."""
import sys; sys.path.insert(0,'/home/ubuntu/tmp-offload/emblem/tools'); from arch import *
import collections
CI = {c: i for i, c in enumerate(CP)}
def within(y, X, cell):
    # demean by cell
    y = y.astype(float).copy(); X = X.astype(float).copy()
    u, inv = np.unique(cell, return_inverse=True)
    cnt = np.bincount(inv)
    for arr in [y] + [X[:, j] for j in range(X.shape[1])]:
        mu = np.bincount(inv, arr) / cnt; arr -= mu[inv]
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ b
    # cluster-robust by cell
    XtX = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    sc = np.zeros((len(u), X.shape[1]))
    np.add.at(sc, inv, X * e[:, None])
    meat = sc.T @ sc
    V = XtX @ meat @ XtX
    return b, np.sqrt(np.diag(V))
def run(days, team, ty, pre=50, post=(200, 400), key=lambda e, r: fam(e[0]).split('-')[0], base=None, minn=100):
    rows = []
    for d in days:
        S, U, m = day(d)
        s = (U['team'] == team) & (U['type'] == ty) & (U['kind'] == 1) if 'kind' in U else (U['team'] == team) & (U['type'] == ty)
        row = U['row'][s]
        for i, j in enumerate(np.nonzero(s)[0]):
            rows.append((d, S['map'][row[i]], S['side'][row[i]], key(U['e'][j], U['r'][j]), S['gold'][row[i]], S['ogold'][row[i]], S['win'][row[i]], S['orating'][row[i]], U['opp'][j], S['rounds'][row[i]]))
    lab = np.array([r[3] for r in rows]); cnt = collections.Counter(lab)
    cats = [c for c, n in cnt.most_common() if n >= minn]
    base = base or cats[0]
    keep = np.isin(lab, cats)
    R = [r for r, k in zip(rows, keep) if k]; lab = lab[keep]
    gold = np.array([r[4] for r in R]); ogold = np.array([r[5] for r in R])
    cell = np.array([f'{r[0][-2:]}:{r[1]}:{r[2]}' for r in R])
    orat = np.array([r[7] for r in R])
    out = {}
    D = np.stack([(lab == c) for c in cats if c != base], 1)
    ctrl = np.stack([gold[:, CI[pre]], ogold[:, CI[pre]], orat], 1)
    ok = np.isfinite(ctrl).all(1)
    print(f'{team[:12]} {ty} pre=r{pre} base={base} n={ok.sum()} cats=' + ' '.join(f'{c}:{cnt[c]}' for c in cats))
    for name, y, okk in [(f'gold{p}', gold[:, CI[p]], np.isfinite(gold[:, CI[p]])) for p in post] + [('win', np.array([r[6] for r in R]), np.ones(len(R), bool))]:
        k = ok & okk
        b, se = within(y[k], np.concatenate([D[k], ctrl[k]], 1), cell[k])
        print(f'   {name:8s} ' + ' '.join(f'{c}:{b[i]:+.3f}±{se[i]:.3f}' if name == 'win' else f'{c}:{b[i]:+.0f}±{se[i]:.0f}' for i, c in enumerate([c for c in cats if c != base])), f'(n={k.sum()}, survivors)')
if __name__ == '__main__':
    days = sys.argv[1].split(','); team = sys.argv[2]; ty = sys.argv[3]; pre = int(sys.argv[4]) if len(sys.argv) > 4 else 50
    run(days, team, ty, pre)
