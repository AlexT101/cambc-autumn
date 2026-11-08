# Do camp-group features carry a per-map signal for the context knobs (mid_gold, invade deny)? Read-only use of the
# ctxknob agent's per-game A/B rows (~/tmp-offload/ctxknob/ana/*.pkl). Per arm: the cand's win on z(feature), with the
# knob agent's cells (one-site; spawn walk <= 40 / 40-73 / > 73) as covariates, so a slope is signal beyond them.
#   python knobs.py CTXMAPS.jsonl
import sys, json, pickle, collections, numpy as np
A = '/home/ubuntu/tmp-offload/ctxknob/ana/'
F = {}
for l in open(sys.argv[1]):
    r = json.loads(l); F['/home/ubuntu/cambc-autumn/' + r['path']] = r['f']
sites = {}
for l in open(A + 'sites.jsonl'):
    r = json.loads(l); sites[r['file']] = r['sites']
NEW = ['gem_groups', 'one_gem_group', 'gold_groups', 'one_gold_group', 'hv_compact', 'hv_rate', 'hv_val', 'hv_share']
LOG = {'gem_groups', 'gold_groups', 'hv_val'}
GROUPS = {'mid_gold b23 (vs 1.0)': ('gold2.pkl', ['m125dec', 'm15dec', 'm125conf', 'm125conf2', 'm15conf', 'm15dev', 'm15dev2', 'm125dev2', 'm20dev']),
          'mid_gold b25 mirror (vs 1.25)': ('gold2.pkl', ['m150mir', 'm175mir']),
          'mid_gold b25 panel (arm-td minus base-td)': ('goldpanel.pkl', None),
          'deny old (d50 vs oc-base1)': ('deny.pkl', ['old50']),
          'deny b25 (d50/d25)': ('deny.pkl', ['d50f1', 'd50f2', 'd25f1', 'd25f2'])}
def logit_fit(X, y):
    th = np.zeros(X.shape[1])
    for _ in range(25):
        p = 1 / (1 + np.exp(-X @ th)); H = (X * (p * (1 - p))[:, None]).T @ X + 1e-6 * np.eye(len(th))
        d = np.linalg.solve(H, X.T @ (p - y)); th -= d
        if np.abs(d).max() < 1e-8: break
    return th, np.sqrt(np.diag(np.linalg.inv(H)))
cache = {}
for gname, (pk, labels) in GROUPS.items():
    if pk not in cache: cache[pk] = pickle.load(open(A + pk, 'rb'))
    d = cache[pk]; rows = d['rows']; feat = d['feat']
    if pk == 'goldpanel.pkl':
        # arm-td games against a member, sign +1; oc-base25-td's games against the same member, sign -1 (a difference)
        sel = [(r, +1 if r[0].startswith('m1') and not r[0].endswith('b') else -1) for r in rows if not r[0].endswith('b')]
    else:
        sel = [(r, 1) for r in rows if r[0] in labels]
    sel = [(r, s) for r, s in sel if r[1] in F and r[1] in feat]
    if not sel: print(gname, 'no rows'); continue
    y = np.array([r[3] for r, _ in sel], float); sg = np.array([s for _, s in sel], float)
    sd = np.array([feat[r[1]].get('spawn_dist', 0) or 0 for r, _ in sel], float)
    one = np.array([sites.get(r[1], 2) == 1 for r, _ in sel], float)
    cells = np.stack([one, (1 - one) * (sd <= 40), (1 - one) * (sd > 40) * (sd <= 73), (1 - one) * (sd > 73)], 1)
    labs = sorted(set(r[0] for r, _ in sel)); L = np.array([[r[0] == l for l in labs] for r, _ in sel], float)
    print(f'## {gname}: {len(sel)} games, {len(set(r[1] for r, _ in sel))} maps')
    for k in NEW:
        v = np.array([F[r[1]][k] for r, _ in sel], float); v = np.log1p(v) if k in LOG else v
        z = (v - v.mean()) / (v.std() or 1)
        # a label x cell intercept per label, plus a shared slope (sign-flipped for the panel's base rows)
        C = (L[:, :, None] * cells[:, None, :]).reshape(len(y), -1); C = C[:, C.sum(0) > 0]
        X = np.hstack([C, (z * (sg > 0))[:, None], (z * (sg < 0))[:, None]]) if (sg < 0).any() else np.hstack([C, z[:, None]])
        th, se = logit_fit(X, y)
        b, e = (th[-2] - th[-1], np.hypot(se[-2], se[-1])) if (sg < 0).any() else (th[-1], se[-1])
        print(f'   {k:15s} slope {25 * b:+.2f} pts/SD (se {25 * e:.2f}, z {b / e:+.1f})')
