# Split-half value of adding new map features to ocean's draft (oc-base25 = draft7-f92, counters off).
# New champion x feature weights are fitted on top of F92's logits (offset), separately on each map half
# (hash(key#half) % 2). Each map's team is chosen with F92 + the other half's weights (pysim, the C++-matched draft)
# and valued with F92 + its own half's weights, against F92's own team. 'self' values with the choosing weights
# (the optimizer's curse).
#   python select.py INSAMPLE.txt BASES.txt MAPS.jsonl [LAM] [SETS]
import sys, json, itertools, numpy as np
sys.path.insert(0, '/home/ubuntu/tmp-offload/counter2/sim')
from pysim import draft, PIDX
pred, basesf, mapsf = sys.argv[1:4]; LAM = float(sys.argv[4]) if len(sys.argv) > 4 else 320
NEW = [('gem_groups', 'log1p'), ('one_gem_group', None), ('gold_groups', 'log1p'), ('one_gold_group', None),
       ('hv_compact', None), ('hv_rate', None), ('hv_val', 'log1p'), ('hv_share', None)]
SETS = {'hv_compact': [4], 'hv_rate': [5], 'hv_compact+rate': [4, 5], 'hv4': [4, 5, 6, 7], 'counts4': [0, 1, 2, 3], 'all8': list(range(8))}
if len(sys.argv) > 5: SETS = {k: v for k, v in SETS.items() if k in sys.argv[5].split(',')}
PTS = 25
raw, ladder = {}, set()
for l in open(mapsf):
    r = json.loads(l)
    if r['picks'] not in (3, 4, 5): continue
    raw[r['key']] = [(np.log1p(max(r['f'][n], 0)) if tf == 'log1p' else r['f'][n]) for n, tf in NEW]
    if r['set'] == 'maps': ladder.add(r['key'])
keys = list(raw); Z = np.array([raw[k] for k in keys], float)
Z = np.clip((Z - Z.mean(0)) / np.where(Z.std(0) > 0, Z.std(0), 1), -4, 4); zi = {k: i for i, k in enumerate(keys)}
SYN, BASE = {}, {}
for l in open(basesf):
    x = l.split()
    if x[0] == 'S': SYN[int(x[1])] = np.array(list(map(float, x[2:])))
    elif int(x[2]) == int(x[3]): BASE[x[1]] = (int(x[2]), np.array(list(map(float, x[4:]))))
K, P, W, E, H, S = [], [], [], [], [], []
for l in open(pred):
    x = l.split()
    K.append(zi[x[0]]); P.append(int(x[1])); W.append(int(x[2])); E.append(float(x[3])); H.append(int(x[7]))
    a = np.zeros(12); a[[int(c) for c in x[4].split(',')]] += 1; a[[int(c) for c in x[5].split(',')]] -= 1; S.append(a)
K, P, W, E, H, S = map(np.array, (K, P, W, E, H, S)); S = S.astype(np.float32)
mh = {}
for k, h in zip(K.tolist(), H.tolist()): mh[k] = h
print(f'{len(K)} games, {len(mh)} maps with games', flush=True)
def newton(X, y, off, lam, th0):
    th = th0.copy()
    for _ in range(30):
        e = off + X @ th; p = 1 / (1 + np.exp(-e)); g = X.T @ (p - y) + lam * (th - th0)
        Hs = (X * (p * (1 - p))[:, None]).T @ X + lam * np.eye(len(th)); d = np.linalg.solve(Hs, g); th -= d
        if np.abs(d).max() < 1e-7: break
    return th
def fit(X, m):
    th0 = newton(X[m], W[m], E[m], LAM, np.zeros(X.shape[1]))
    return {p: newton(X[m & (P == p)], W[m & (P == p)], E[m & (P == p)], LAM, th0) for p in (3, 4, 5)}
TEAMS = {p: [tuple(t) for t in itertools.combinations(range(12), p)] for p in (3, 4, 5)}
def score(T, base, syn): return base[list(T)].sum() + sum(syn[PIDX[(a, b)]] for a, b in itertools.combinations(T, 2))
for name, cols in SETS.items():
    X = (S[:, :, None] * Z[K][:, None, cols].astype(np.float32)).reshape(len(K), -1)
    v = {h: fit(X, H == h) for h in (0, 1)}
    res = {'all': [], 'ladder': []}; selfv = []; changed = 0; n = 0
    for key, (p, base) in BASE.items():
        i = zi.get(key)
        if i is None or i not in mh: continue
        h = mh[i]; add = lambda vv: (vv[p].reshape(12, len(cols)) @ Z[i, cols])
        b_other, b_own = base + add(v[1 - h]), base + add(v[h])
        T0 = tuple(sorted(draft(base, p, SYN[p], [], None, off=True)))
        T1 = tuple(sorted(draft(b_other, p, SYN[p], [], None, off=True)))
        T2 = tuple(sorted(draft(b_own, p, SYN[p], [], None, off=True)))
        n += 1; changed += T1 != T0
        val = PTS * (score(T1, b_own, SYN[p]) - score(T0, b_own, SYN[p]))
        res['all'].append(val); selfv.append(PTS * (score(T2, b_own, SYN[p]) - score(T0, b_own, SYN[p])))
        if key in ladder: res['ladder'].append(val)
    a = np.array(res['all']); l = np.array(res['ladder'])
    print(f'{name:16s} teams changed {100 * changed / n:5.1f}% of {n} maps; cross value {a.mean():+.3f} pts (se {a.std() / np.sqrt(len(a)):.3f}); '
          f'self {np.mean(selfv):+.3f}; ladder {len(l)} maps {l.mean():+.3f} changed {100 * np.mean(l != 0):.0f}%', flush=True)
