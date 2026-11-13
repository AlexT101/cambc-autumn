"""Fit the ladder's rating update from consecutive 10-minute groups (archive copy).

Each team plays one 5-game group per tick; g_rating holds both teams' pre-group ratings.
Delta(team) = rating at its next tick - rating at this tick. Compare against
K * (S - n*E) with S = wins, E = 1/(1+10^(-(r - r_opp)/scale)), per game or per group.
Usage: python3 fit_rating.py RANKED.npz
"""
import sys
import numpy as np

z = np.load(sys.argv[1])
cr, a, b, ra, rb, w, day = (z[k] for k in ('created', 'a', 'b', 'ra', 'rb', 'winner', 'day'))
ok = np.isfinite(cr) & np.isfinite(ra) & np.isfinite(rb)
cr, a, b, ra, rb, w, day = (x[ok] for x in (cr, a, b, ra, rb, w, day))
tick = np.round(cr / 600).astype(np.int64)

# Collapse to groups: (tick, a, b)
order = np.lexsort((b, a, tick))
tick, a, b, ra, rb, w, day = (x[order] for x in (tick, a, b, ra, rb, w, day))
brk = np.r_[True, (np.diff(tick) != 0) | (np.diff(a) != 0) | (np.diff(b) != 0)]
gid = np.cumsum(brk) - 1
ng = gid[-1] + 1
G_tick = tick[brk]; G_a = a[brk]; G_b = b[brk]; G_ra = ra[brk].astype(float); G_rb = rb[brk].astype(float)
G_n = np.bincount(gid, minlength=ng)
G_wa = np.bincount(gid, weights=(w == 0), minlength=ng)
G_wb = np.bincount(gid, weights=(w == 1), minlength=ng)
G_day = day[brk]
print('groups', ng, 'sizes', np.bincount(G_n)[:8], 'draw/none games', int((G_n - G_wa - G_wb).sum()))

# Team-side rows: team, tick, own pre, opp pre, wins, n
T = np.r_[G_a, G_b]; TK = np.r_[G_tick, G_tick]; R = np.r_[G_ra, G_rb]; RO = np.r_[G_rb, G_ra]
W = np.r_[G_wa, G_wb]; L = np.r_[G_wb, G_wa]; N = np.r_[G_n, G_n]; D = np.r_[G_day, G_day]
o = np.lexsort((TK, T))
T, TK, R, RO, W, L, N, D = (x[o] for x in (T, TK, R, RO, W, L, N, D))
nxt = (T[1:] == T[:-1]) & (TK[1:] - TK[:-1] == 1)
i = np.where(nxt)[0]
dR = R[i + 1] - R[i]
r, ro, wins, losses, n = R[i], RO[i], W[i], L[i], N[i]
full = (n == 5) & (wins + losses == 5)
print('consecutive pairs', len(i), 'full groups', int(full.sum()))

def pred(K, scale, mode):
    E = 1 / (1 + 10 ** (-(r - ro) / scale))
    if mode == 'group':
        return K * (wins / n - E)
    if mode == 'pergame':
        return K * (wins - n * E)
    raise ValueError

for mode in ('group', 'pergame'):
    best = None
    for scale in (200, 300, 400, 500, 600, 800):
        E = 1 / (1 + 10 ** (-(r - ro) / scale))
        x = (wins / n - E) if mode == 'group' else (wins - n * E)
        m = full
        K = (x[m] * dR[m]).sum() / (x[m] ** 2).sum()
        res = dR[m] - K * x[m]
        rms = np.sqrt((res ** 2).mean())
        print(f'{mode:8s} scale {scale:4d}  K {K:8.3f}  rms {rms:.4f}  |res|<0.01 {np.mean(np.abs(res) < 0.01):.3f}')
        if best is None or rms < best[0]:
            best = (rms, scale, K)
    print('best', mode, best)

# Sequential per-game Elo with the opponent's rating fixed at pre-group: check exactness
scale = 400
for K in (6.4, 32 / 5):
    E = 1 / (1 + 10 ** (-(r - ro) / scale))
    p = K * (wins - 5 * E)
    res = dR[full] - p[full]
    print('K', K, 'median |res|', np.median(np.abs(res)), 'p99', np.percentile(np.abs(res), 99), 'max', np.abs(res).max())

# residual by rating level / by day (any rating-dependent K or provisional period?)
E = 1 / (1 + 10 ** (-(r - ro) / 400))
p = 32 * (wins / 5 - E)
res = dR - p
for lo, hi in ((0, 1500), (1500, 2000), (2000, 2500), (2500, 3200)):
    m = full & (r >= lo) & (r < hi)
    if m.sum():
        print(f'rating {lo}-{hi}: n {m.sum()} median|res| {np.median(np.abs(res[m])):.4f} p95 {np.percentile(np.abs(res[m]), 95):.3f}')
for d in np.unique(D[i]):
    m = full & (D[i] == d)
    if m.sum():
        print(d, m.sum(), f'{np.median(np.abs(res[m])):.4f}', f'{np.percentile(np.abs(res[m]), 95):.3f}')

# Tail: is a large residual explained by the previous group's result landing late (applied at t+2)?
m = full
big = m & (np.abs(res) > 0.01)
print('share |res|>0.01:', big.sum() / m.sum())
# two-step check: R[t+2]-R[t] vs p_t + p_{t+1}
j = np.where(nxt[:-1] & nxt[1:])[0]
p_all = np.zeros(len(T)); E_all = 1 / (1 + 10 ** (-(R - RO) / 400)); p_all = 32 * (W / np.maximum(N, 1) - E_all)
two = R[j + 2] - R[j]
res2 = two - p_all[j] - p_all[j + 1]
print('two-step |res|<0.01 share', np.mean(np.abs(res2) < 0.01), 'one-step share', np.mean(np.abs(R[j+1]-R[j]-p_all[j]) < 0.01))

# Cumulative check: over runs of consecutive ticks, actual change vs summed Elo predictions.
runs = np.r_[True, ~nxt]  # run starts
run_id = np.cumsum(runs) - 1
pa = p_all
act = []
for rid in np.unique(run_id[(R > 2400)])[:4000]:
    idx_ = np.where(run_id == rid)[0]
    if len(idx_) < 50:
        continue
    act.append((R[idx_[-1]] - R[idx_[0]], pa[idx_[:-1]].sum(), len(idx_)))
act = np.array(act)
if len(act):
    print('runs', len(act), 'median |actual - summed pred| over runs of median length', np.median(act[:, 2]), ':', np.median(np.abs(act[:, 0] - act[:, 1])),
          'median |actual|', np.median(np.abs(act[:, 0])))
# Residual vs the previous tick's prediction (late application signature)
k = np.where(nxt[1:] & nxt[:-1])[0] + 1  # k has a predecessor transition k-1
r1 = (R[k + 1] - R[k]) - pa[k]
print('corr(res_t, pred_{t-1}) ', np.corrcoef(r1, pa[k - 1])[0, 1], ' corr(res_t, -pred_t)', np.corrcoef(r1, -pa[k])[0, 1])
