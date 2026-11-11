"""Ranked ladder games against Fish and Mite, every team (big-arm archive, 11-06..11-11): does the opposing team's
draft change its result against them?  win ~ team + (map, side) cell + champion held. Teams differ in their picks
on the same cell, so the cell effect holds the map fixed and the team effect the bot. The same model on the same
teams' games against everyone else gives the champion's general value; the difference is what is specific to
Fish or Mite.
    py ladder.py [ladder-all.jsonl]"""
import json, sys, collections, numpy as np
from scipy import sparse
from scipy.sparse.linalg import lsqr
SRC = sys.argv[1] if len(sys.argv) > 1 else '/home/ubuntu/tmp-offload/draftnudge/work/ladder-all.jsonl'
CH = ['Cassi & Issac', 'Prism', 'Willow', 'Vesper Vale', 'Heart of Ruin', 'Vendetta', 'Marcella', 'Ryth', 'Ren', 'Varg', 'Tavi', 'Stellar']
F, M = 'Intercontinental Fish', 'Mite'
rng = np.random.default_rng(2)
R = collections.defaultdict(list); top = set()
for l in open(SRC):
    g = json.loads(l)
    if g['opp'] in (F, M): top.add(g['team'])
rows = []
for l in open(SRC):
    g = json.loads(l)
    if g['team'] in top and g['team'] not in (F, M) and g['opp_rank'] <= 30: rows.append(g)
for g in rows: R[g['opp'] if g['opp'] in (F, M) else 'field'].append(g)
def fit(gs, s=None):
    if s is not None: gs = [gs[i] for i in s]
    t = {x: i for i, x in enumerate(sorted({g['team'] for g in gs}))}; c = {x: i for i, x in enumerate(sorted({(g['map'], g['side']) for g in gs}))}
    n = len(gs); r, cc, v = [], [], []
    for i, g in enumerate(gs):
        r += [i, i]; cc += [t[g['team']], len(t) + c[(g['map'], g['side'])]]; v += [1, 1]
        for p in g['picks']: r.append(i); cc.append(len(t) + len(c) + CH.index(p)); v.append(1)
    A = sparse.csr_matrix((v, (r, cc)), shape=(n, len(t) + len(c) + 12)); y = np.array([float(g['win']) for g in gs])
    b = lsqr(A, y, atol=1e-10, btol=1e-10, iter_lim=3000)[0][-12:]
    return b - b.mean()
def bootfit(gs, n=300):
    mp = collections.defaultdict(list)
    for i, g in enumerate(gs): mp[g['map']].append(i)
    um = sorted(mp); out = []
    for _ in range(n):
        s = [i for j in rng.integers(0, len(um), len(um)) for i in mp[um[j]]]; out.append(fit(gs, s))
    return np.array(out)
res = {}
for k in (F, M, 'field'):
    gs = R[k]; b = fit(gs); B = bootfit(gs); res[k] = (b, B)
    print(f'\n**against {k}**: {len(gs)} games, {len({g["team"] for g in gs})} teams, they won {100 * np.mean([g["win"] for g in gs]):.1f}%; pair held {100 * np.mean(["Cassi & Issac" in g["picks"] for g in gs]):.0f}%')
    print('  per team, pair held / not: ' + '; '.join(f'{t[:10]} {sum("Cassi & Issac" in g["picks"] for g in gs if g["team"] == t)}/{sum("Cassi & Issac" not in g["picks"] for g in gs if g["team"] == t)}' for t in sorted({g['team'] for g in gs}) if sum(g['team'] == t for g in gs) >= 60))
    for i in np.argsort(-b):
        lo, hi = np.percentile(B[:, i], [2.5, 97.5]); print(f'  {CH[i]:14s} {100 * b[i]:+6.1f} ({100 * lo:+6.1f} to {100 * hi:+6.1f})   held {100 * np.mean([CH[i] in g["picks"] for g in gs]):.0f}%' + ('  *' if lo > 0 or hi < 0 else ''))
for k in (F, M):
    print(f'\n**{k} minus field** (what is specific to this opponent)')
    b = res[k][0] - res['field'][0]; se = np.sqrt(res[k][1].var(0) + res['field'][1].var(0))
    for i in np.argsort(-b): print(f'  {CH[i]:14s} {100 * b[i]:+6.1f} ({100 * (b[i] - 1.96 * se[i]):+6.1f} to {100 * (b[i] + 1.96 * se[i]):+6.1f})' + ('  *' if abs(b[i]) > 1.96 * se[i] else ''))
# our own ranked games
print()
for k in (F, M):
    gs = [g for g in R[k] if g['team'].startswith('stellar best girl')]
    for c in CH:
        h = [g['win'] for g in gs if c in g['picks']]; nh = [g['win'] for g in gs if c not in g['picks']]
        if len(h) >= 15 and len(nh) >= 15: print(f'  our ranked games against {k[:5]}: {c:14s} held {100 * np.mean(h):.0f}% of {len(h)}, not held {100 * np.mean(nh):.0f}% of {len(nh)}')
