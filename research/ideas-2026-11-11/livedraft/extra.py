"""Three tighter reads of the 502 draft step (v83-114 -> v115) from the live scrims:
  (a) the changed-cell effect holding the cell's old win share fixed (logistic on the old share's logit),
  (b) the commonest single swaps, each against the unchanged cells,
  (c) the same difference of differences on our deaths and the kill margin (a finer outcome than win/loss).
    py extra.py"""
import json, collections, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cells import load, CH, boot, cellsof
G = load(); D2 = set(range(83, 115)); rng = np.random.default_rng(3)
def table(opp, refs_old, refs_new, old=D2, new={115}, sameopp=False):
    O, N = cellsof(G, opp, refs_old, old), cellsof(G, opp, refs_new, new); rows = []
    for k in sorted(set(O) & set(N)):
        n = N[k][0]; o = [g for g in O[k] if not sameopp or g['oteam'] == n['oteam']]
        if not o or len({g['team'] for g in o}) != 1: continue
        f = lambda gs, key: np.mean([g.get(key) or 0 for g in gs])
        rows.append(dict(map=k[0], side=k[1], old=o[0]['team'], new=n['team'], changed=o[0]['team'] != n['team'], po=np.mean([g['w'] for g in o]), pn=n['w'], no=len(o),
                         do=f(o, 'opp_kills'), dn=f([n], 'opp_kills'), ko=f(o, 'our_kills'), kn=f([n], 'our_kills')))
    return rows
T = {'Fish': table('Inte', {'r1', 'r2'}, {'r2'}), 'Mite': table('Mite', {'r3', 'r4', 'r5', 'r6'}, {'r6'}, sameopp=True)}

def logit_fit(X, y, it=50):
    b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); W = p * (1 - p) + 1e-9
        b = b + np.linalg.solve(X.T @ (X * W[:, None]) + 1e-6 * np.eye(len(b)), X.T @ (y - p))
    return b
print('## (a) v115 won ~ logit(old share, shrunk) + changed: the changed-cell effect at a 65% cell, in win points\n')
for nm, rows in T.items():
    m = np.array([r['map'] for r in rows]); ch = np.array([float(r['changed']) for r in rows]); y = np.array([r['pn'] for r in rows])
    ps = np.array([(r['po'] * r['no'] + 0.65) / (r['no'] + 1) for r in rows]); lg = np.log(ps / (1 - ps))
    def f(s):
        b = logit_fit(np.column_stack([np.ones(len(s)), lg[s], ch[s]]), y[s]); base = np.log(0.65 / 0.35)
        return 1 / (1 + np.exp(-(base + b[2]))) - 0.65
    e = f(np.arange(len(y))); lo, hi = boot(m, f, 600)
    print(f'{nm}: {100 * e:+.1f} ({100 * lo:+.1f} to {100 * hi:+.1f}) on {int(ch.sum())} changed cells; old share predicts v115: corr {np.corrcoef(ps, y)[0, 1]:+.2f}')

print('\n## (b) single swaps at the 502 step (cells where exactly one pick changed, and all cells with the swap among their changes)\n')
print('| swap (out -> in) | cells | Fish old -> v115 | net of unchanged cells | Mite old -> v115 | net of unchanged cells |\n|---|---:|---|---|---|---|')
key = lambda r: (tuple(sorted(set(r['old']) - set(r['new']))), tuple(sorted(set(r['new']) - set(r['old']))))
cnt = collections.Counter(key(r) for r in T['Fish'] if r['changed'])
def net(rows, sel):
    m = np.array([r['map'] for r in rows]); d = np.array([r['pn'] - r['po'] for r in rows]); a = np.array([sel(r) for r in rows]); u = np.array([not r['changed'] for r in rows])
    f = lambda s: d[s][a[s]].mean() - d[s][u[s]].mean()
    lo, hi = boot(m, f, 600); po = np.mean([r['po'] for r, x in zip(rows, a) if x]); pn = np.mean([r['pn'] for r, x in zip(rows, a) if x])
    return f'{100 * po:.0f} -> {100 * pn:.0f}', f'{100 * f(np.arange(len(d))):+.0f} ({100 * lo:+.0f} to {100 * hi:+.0f})', int(a.sum())
for k, n in cnt.most_common(8):
    a = net(T['Fish'], lambda r: key(r) == k); b = net(T['Mite'], lambda r: key(r) == k)
    print(f'| {", ".join(k[0])} -> {", ".join(k[1])} | {n} | {a[0]} | {a[1]} | {b[0]} | {b[1]} |')
for out, inn in (('Heart of Ruin', 'Willow'), ('Heart of Ruin', 'Ryth'), ('Ren', 'Ryth'), ('Heart of Ruin', None), (None, 'Willow'), (None, 'Ryth'), ('Cassi & Issac', None), ('Marcella', None), ('Ren', None)):
    sel = lambda r: r['changed'] and (out is None or (out in r['old'] and out not in r['new'])) and (inn is None or (inn in r['new'] and inn not in r['old']))
    a = net(T['Fish'], sel); b = net(T['Mite'], sel)
    print(f'| any change with {out or "*"} -> {inn or "*"} | {a[2]} | {a[0]} | {a[1]} | {b[0]} | {b[1]} |')

print('\n## (c) deaths: our deaths a game and kill margin (ours - theirs), old -> v115, changed cells net of unchanged\n')
print('| opponent | our deaths, changed cells | unchanged cells | draft effect on our deaths | kill margin, changed | unchanged | draft effect on the margin |\n|---|---|---|---|---|---|---|')
for nm, rows in T.items():
    m = np.array([r['map'] for r in rows]); ch = np.array([r['changed'] for r in rows])
    dd = np.array([r['dn'] - r['do'] for r in rows]); mm = np.array([(r['kn'] - r['dn']) - (r['ko'] - r['do']) for r in rows])
    out = []
    for d, a, b in ((dd, 'do', 'dn'), (mm, None, None)):
        f = lambda s: d[s][ch[s]].mean() - d[s][~ch[s]].mean(); lo, hi = boot(m, f, 1000)
        if a: lv = lambda sel: f'{np.mean([r[a] for r, c in zip(rows, ch) if c == sel]):.1f} -> {np.mean([r[b] for r, c in zip(rows, ch) if c == sel]):.1f}'
        else: lv = lambda sel: f'{np.mean([r["ko"] - r["do"] for r, c in zip(rows, ch) if c == sel]):+.1f} -> {np.mean([r["kn"] - r["dn"] for r, c in zip(rows, ch) if c == sel]):+.1f}'
        out += [lv(True), lv(False), f'{f(np.arange(len(d))):+.2f} ({lo:+.2f} to {hi:+.2f})']
    print(f'| {nm} | ' + ' | '.join(out) + ' |')
    # champion swaps on our deaths
    X = np.array([[float(c in r['new']) - float(c in r['old']) for c in CH] for r in rows]); use = [j for j in range(12) if np.abs(X[:, j]).sum() >= 12]
    def fit(s):
        b = np.linalg.lstsq(np.column_stack([np.ones(len(s)), X[s][:, use]]), dd[s], rcond=None)[0][1:]; return b - b.mean()
    b = fit(np.arange(len(dd))); lo, hi = boot(m, fit, 600)
    print('  our deaths a game for holding (centred): ' + ', '.join(f'{CH[j]} {b[i]:+.1f} ({lo[i]:+.1f} to {hi[i]:+.1f})' + ('*' if lo[i] > 0 or hi[i] < 0 else '') for i, j in sorted(enumerate(use), key=lambda t: -b[t[0]])))
