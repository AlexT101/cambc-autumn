# score.py CVDIR: score tests for champion x g(map) terms missing from the base model (set 0), on its out-of-fold residuals.
# g is projected off [1, z] (the model's linear map terms) at map level, weighted by games, so a term the model already has
# scores ~0. z per (champion, g) = sum (y - p) (A_c - B_c) g / sqrt(sum p (1 - p) (A_c - B_c)^2 g^2). Also a joint chi2 per g
# over the 12 champions (sum of z^2, ignoring their correlation).
import json, sys, math
import numpy as np

D = '/tmp/claude-1000/-home-ubuntu-cambc-autumn/3650a530-f591-417e-a0c5-31524a1e3260/scratchpad/df'
cv = sys.argv[1]
si = int(sys.argv[2]) if len(sys.argv) > 2 else 0
z = np.load(f'{D}/games.npz')
mi, A, B, win, MF, mfold = z['mi'], z['A'].astype(np.float64), z['B'].astype(np.float64), z['win'].astype(np.float64), z['MF'], z['mfold']
fnames = list(z['fnames'])
s0 = json.load(open(f'{cv}/set{si}.json'))
mean, sd = np.array(s0['mean'][:25]), np.array(s0['sd'][:25])
Z = (MF[:, :25] - mean) / sd
Z = np.where(np.isfinite(Z), np.clip(Z, -4, 4), 0.0)
fold = mfold[mi]
e = np.zeros(len(win))
for k in range(5):
    lg = np.fromfile(f'{cv}/logits_s{si}_f{k}.f32', dtype=np.float32).astype(np.float64)
    e[fold == k] = lg[fold == k]
p = 1 / (1 + np.exp(-e))
r, w = win - p, p * (1 - p)
Dc = A - B
CH = ['Ryth', 'Vesp', 'Vend', 'Cass', 'Stel', 'Pris', 'Marc', 'Will', 'Ren', 'Varg', 'Tavi', 'HoR']
alt = MF[:, 25]
names = fnames[:25]
cands = {'one_altar': (alt == 1) * 1.0, 'two_altar': (alt == 2) * 1.0, 'odd_altar': (alt % 2 == 1) * 1.0, 'altars34': ((alt == 3) | (alt == 4)) * 1.0,
         'altars5p': (alt >= 5) * 1.0}
for j in range(25): cands[f'sq_{names[j]}'] = Z[:, j] ** 2
for i in range(25):
    for j in range(i + 1, 25): cands[f'{names[i]}*{names[j]}'] = Z[:, i] * Z[:, j]
# Extra raw metrics not in the model (log1p of the nonnegative ones), as candidates for new linear features.
for j in range(26, len(fnames)):
    v = MF[:, j]
    v = np.log1p(np.maximum(v, 0)) if np.nanmin(v) >= 0 else v
    m_, s_ = np.nanmean(v), np.nanstd(v) or 1
    cands[f'x_{fnames[j]}'] = np.where(np.isfinite(v), np.clip((v - m_) / s_, -4, 4), 0)
nm_games = np.bincount(mi, minlength=len(MF)).astype(np.float64)
def cname(n):
    if n.startswith('pr_'): a, b = n[3:].split('__'); return f'{a}*{b}'
    if n.startswith('l_') or n == 'walls': return 'x_' + n.replace('l_', '')
    return n
extra_cols = [cands[cname(n)] for n in s0['features'][25:]]
X1 = np.concatenate([np.ones((len(MF), 1)), Z] + [c[:, None] for c in extra_cols], axis=1)
print('projected off', 26 + len(extra_cols), 'columns')
WX = X1 * nm_games[:, None]
G = np.linalg.solve(X1.T @ WX + 1e-9 * np.eye(X1.shape[1]), np.eye(X1.shape[1]))
out = []
for name, g in cands.items():
    gp = g - X1 @ (G @ (WX.T @ g))
    gr = gp[mi]
    U = (r * gr) @ Dc
    V = (w * gr * gr) @ (Dc * Dc)
    zs = U / np.sqrt(V)
    out.append((float((zs ** 2).sum()), name, zs))
out.sort(key=lambda x: -x[0])
print('chi2(12) | g | top champions by z')
for chi, name, zs in out[:45]:
    top = sorted(range(12), key=lambda c: -abs(zs[c]))[:4]
    print(f'{chi:8.1f} | {name} | ' + ', '.join(f'{CH[c]} {zs[c]:+.1f}' for c in top))
json.dump([(n, c, list(map(float, zs))) for c, n, zs in out], open(f'{cv}/score_s{si}.json', 'w'))
print('rank of one_altar', [i for i, o in enumerate(out) if o[1] == 'one_altar'], 'of', len(out))
