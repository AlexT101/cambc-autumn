"""What in a map makes BattleCats (current version) pick each champion? Its draft is a fixed function of (map, side)."""
import collections, json, meta, fl
import numpy as np
G = fl.load(lambda g: True)
mh = {}
for g in G: mh[g['map']] = g
R = [r for r in meta.rows() if r['kind'] == 'ranked' and r['created_at'] >= '2026-11-10T09']
cell = {}
for r in R: cell[(r['map'], r['bc_side'])] = r['bc_picks']
X = []; Y = []; names = None
def feats(g, side):
    t = 0 if side == 'a' else 1
    groups = g['groups']
    so = fl.spawn_c(g, t)
    gem = sum(q[2] for q in groups); gold = sum(q[3] for q in groups)
    f = collections.OrderedDict()
    f['picks'] = None
    f['area'] = g['W'] * g['H']
    f['altars'] = len(g['altars'])
    f['altar_dist_min'] = min(fl.cheb(a, so) for a in g['altars'])
    f['gems_total'] = gem; f['gold_total'] = gold
    f['gem_clusters'] = sum(q[1].count('Gem cluster') for q in groups)
    f['golem'] = sum(q[1].count('Golem') for q in groups); f['monolith'] = sum(q[1].count('Monolith') for q in groups)
    f['elk'] = sum(q[1].count('Elk') for q in groups); f['wolf'] = sum(q[1].count('Wolf') for q in groups)
    f['groups'] = len(groups)
    f['enemy_dist'] = fl.cheb(so, fl.spawn_c(g, 1 - t))
    return f
for (m, s), p in cell.items():
    if m not in mh: continue
    f = feats(mh[m], s); f['picks'] = len(p)
    names = list(f); X.append([f[k] for k in names]); Y.append(set(p))
X = np.array(X, float)
print(len(X), 'map-sides with a decoded map')
for ch in (5, 7, 6, 2, 9, 1, 0, 11, 3):
    y = np.array([ch in s for s in Y])
    if y.sum() < 3 or y.all(): print(meta.CH[ch], 'present', y.mean()); continue
    print(f'\n{meta.CH[ch]}: present in {y.mean():.0%}')
    for j, k in enumerate(names):
        a, b = X[y, j].mean(), X[~y, j].mean()
        print(f'   {k:15s} with {a:8.1f}  without {b:8.1f}')
try:
    from sklearn.tree import DecisionTreeClassifier, export_text
    from sklearn.model_selection import cross_val_score
    for ch in (5, 7, 6, 2, 9, 1, 0):
        y = np.array([ch in s for s in Y])
        t = DecisionTreeClassifier(max_depth=2, min_samples_leaf=8).fit(X, y)
        cv = cross_val_score(DecisionTreeClassifier(max_depth=2, min_samples_leaf=8), X, y, cv=5).mean()
        print(f'\n{meta.CH[ch]} depth-2 tree: cv acc {cv:.2f} (base {max(y.mean(), 1 - y.mean()):.2f})')
        print(export_text(t, feature_names=names))
except ImportError: print('no sklearn')
