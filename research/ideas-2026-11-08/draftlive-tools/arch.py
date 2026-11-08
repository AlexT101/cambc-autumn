# Archive: other teams' games against Fish/Mite. Logit(win vs them) ~ rating diff + team FE + (map, opp) FE + our champs.
import pickle, numpy as np, collections
g = pickle.load(open('/home/ubuntu/tmp-offload/counter/games.pkl', 'rb'))
T = {'1890540d-1ffc-4847-adbf-d0d08772f268': 'F', 'ee83f5e5-bcad-4923-86b4-b79ea6083d2e': 'M'}
US = '547efb5b-57e5-4355-8501-3b331f506d62'
CH = ['Ryth','Vesp','Vend','C&I','Stel','Pris','Marc','Will','Ren','Varg','HoR','Tavi']
rows = []
for r in g['rows']:
    if r['day'] < '2026-11-05': continue
    for me, them, pm, pt, rm, rt, w in ((r['A'], r['B'], r['pa'], r['pb'], r['ra'], r['rb'], r['winner'] == 0), (r['B'], r['A'], r['pb'], r['pa'], r['rb'], r['ra'], r['winner'] == 1)):
        if them in T and me not in T and me != US and pm and len(pm) == len(pt):
            rows.append((me, T[them], r['map'], tuple(pm), (rm - rt) / 400, int(w), r['day']))
print(len(rows), 'games; win', np.mean([x[5] for x in rows]))
teams = {t: i for i, t in enumerate(sorted({(x[0], x[6]) for x in rows}))}
cells = {c: i for i, c in enumerate(sorted({(x[1], x[2]) for x in rows}))}
nT, nC = len(teams), len(cells)
p = 1 + 12 + nT + nC
X = np.zeros((len(rows), p)); y = np.array([x[5] for x in rows], float)
for i, (me, o, m, pm, rd, w, d) in enumerate(rows):
    X[i, 0] = rd
    for c in pm: X[i, 1 + c] = 1
    X[i, 13 + teams[(me, d)]] = 1; X[i, 13 + nT + cells[(o, m)]] = 1
lam = np.r_[0.01, np.full(12, 1.0), np.full(nT, 1.0), np.full(nC, 1.0)]
th = np.zeros(p)
for it in range(30):
    z = X @ th; pr = 1 / (1 + np.exp(-z)); wv = pr * (1 - pr)
    H = X.T @ (X * wv[:, None]) + np.diag(lam); gr = X.T @ (y - pr) - lam * th
    d = np.linalg.solve(H, gr); th += d
    if abs(d).max() < 1e-6: break
se = np.sqrt(np.diag(np.linalg.inv(H)))
cnt = X[:, 1:13].sum(0)
print('rating/400', round(th[0], 3))
for c in np.argsort(-th[1:13]): print(f'{CH[c]:5s} {th[1+c]:+.3f} ±{se[1+c]:.3f}  n={int(cnt[c])}')
