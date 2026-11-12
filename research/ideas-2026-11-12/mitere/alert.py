"""What separates Mite's alert state (priority base 0) from contact (94-99) and retreat: a shallow tree on turn context."""
import p2l, collections, mprio, numpy as np, sys
from sklearn.tree import DecisionTreeClassifier, export_text
I = p2l.I
X, Y = [], []
TY = ['Cassi', 'Issac', 'Vesper Vale', 'Heart of Ruin', 'Tavi', 'Vendetta', 'Marcella', 'Prism', 'Willow', 'Varg']
for g in p2l.load(lambda g: g['vg'] in ('r7',)):
    for row in g['rows']:
        c = row[I['cid']]
        if g['team'][c] != g['mite'] or row[I['chan']] or row[I['dE']] > 6: continue
        s = mprio.decode(row[I['prio']])[0]
        if s not in ('zero', 'contact', 'retreat', 'kill'): continue
        hpf = row[I['hp0']] / row[I['mhp']]
        X.append([hpf, row[I['g0']], row[I['dE']], row[I['nE5']], row[I['nA5']], row[I['cd0']], row[I['cd1']], row[I['eHp']] or 1, row[I['eG']] or 0,
                  row[I['seen5']], row[I['dmgPrev']], row[I['hitPrev']], row[I['dA0']], row[I['r']], TY.index(g['name'][c]) if g['name'][c] in TY else -1,
                  row[I['dS0']] if row[I['dS0']] is not None else 99])
        Y.append(s)
cols = ['hp', 'bag', 'dE', 'nE5', 'nA5', 'cd0', 'cd1', 'eHp', 'eBag', 'seen5', 'dmgPrev', 'hitPrev', 'dAltar', 'round', 'type', 'dSpawn']
X = np.array(X, dtype=float); Y = np.array(Y)
print(collections.Counter(Y))
for depth in (3, 5, 7):
    clf = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=200, random_state=0).fit(X[::2], Y[::2])
    print(depth, 'held-out accuracy', (clf.predict(X[1::2]) == Y[1::2]).mean())
clf = DecisionTreeClassifier(max_depth=5, min_samples_leaf=300, random_state=0).fit(X, Y)
print(export_text(clf, feature_names=cols, show_weights=False))
imp = sorted(zip(clf.feature_importances_, cols), reverse=True); print(imp[:8])
