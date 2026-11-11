"""Between cells, one draft: v83-v114 all drafted the same team in each (map, side) cell and played it ~31 times
against the same Fish bot (and against Mite's pins). Does a cell's win share follow the team, once the cell's
difficulty against other opponents is held fixed?  Observational: the map chose the team.
    py between.py"""
import json, collections, numpy as np, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cells import load, CH, boot
G = load()
def share(sel):
    c = collections.defaultdict(list)
    for g in G:
        if sel(g): c[(g['map'], g['side'])].append(g)
    return c
D2 = lambda g: 83 <= g['version'] <= 114
F = share(lambda g: D2(g) and g['opp_name'].startswith('Inte')); M = share(lambda g: D2(g) and g['opp_name'].startswith('Mite'))
P = share(lambda g: g['version'] == 113 and (g['refset'] or '').startswith('cmp113'))
keys = sorted(k for k in F if k in M and k in P and len({g['team'] for g in F[k]}) == 1)
team = {k: F[k][0]['team'] for k in keys}
pf, pm, pp = (np.array([np.mean([g['w'] for g in X[k]]) for k in keys]) for X in (F, M, P))
maps = np.array([k[0] for k in keys]); npk = np.array([len(team[k]) for k in keys])
X = np.array([[float(c in team[k]) for c in CH] for k in keys]); Dn = np.array([[float(n == p) for p in (3, 4, 5)] for n in npk])
print(f'{len(keys)} cells, {np.mean([len(F[k]) for k in keys]):.0f} games a cell against Fish, {np.mean([len(M[k]) for k in keys]):.0f} against Mite, {np.mean([len(P[k]) for k in keys]):.0f} against the other nine (v113)')
print(f'win share: Fish {100 * pf.mean():.1f}, Mite {100 * pm.mean():.1f}, other nine {100 * pp.mean():.1f}; cell correlation Fish-Mite {np.corrcoef(pf, pm)[0, 1]:+.2f}, Fish-nine {np.corrcoef(pf, pp)[0, 1]:+.2f}, Mite-nine {np.corrcoef(pm, pp)[0, 1]:+.2f}')
def run(y, ctrl, title):
    def fit(s):
        A = np.column_stack([Dn[s], X[s]] + [c[s] for c in ctrl]); b = np.linalg.lstsq(A, y[s], rcond=None)[0][3:15]
        return b - b.mean()
    b = fit(np.arange(len(y))); lo, hi = boot(maps, fit, 1000)
    print(f'\n**{title}** (win points for holding the champion, centred; 95% over maps; cells holding it)')
    for i in np.argsort(-b): print(f'  {CH[i]:14s} {100 * b[i]:+6.1f} ({100 * lo[i]:+6.1f} to {100 * hi[i]:+6.1f})   {int(X[:, i].sum()):3d} cells' + ('  *' if lo[i] > 0 or hi[i] < 0 else ''))
run(pf, [], 'Fish, pick count only'); run(pf, [pp], 'Fish, holding the cell\'s share against the other nine')
run(pm, [], 'Mite, pick count only'); run(pm, [pp], 'Mite, holding the cell\'s share against the other nine')
run(pf - pm, [], 'Fish minus Mite, same cells'); run(pp, [], 'Other nine, pick count only')
# the pair alone, raw
for nm, p in (('Fish', pf), ('Mite', pm), ('other nine', pp)):
    h = X[:, 0] > 0
    print(f'pair held in {h.sum()} cells, {nm}: {100 * p[h].mean():.1f}%; not held in {(~h).sum()}: {100 * p[~h].mean():.1f}%  ({", ".join(sorted({k[0] for k, x in zip(keys, h) if not x}))})')
