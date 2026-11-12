"""Mite's draft as a function of map features: fit on the old 128 maps' cells, test on the 42 new 05 maps (released
11-11 23:10, so never in any table Mite could have built before its first games there). Table = latest version (ep>=11)."""
import json, glob, os, collections, sys
import numpy as np
import meta
from sklearn.tree import DecisionTreeClassifier, export_text
H = os.path.expanduser('~/tmp-offload')
EP = int(sys.argv[1]) if len(sys.argv) > 1 else 11

def cheb(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
# map name -> decoded map json
name2map = {}
live = json.load(open(f'{H}/mitefit/live/rows-r7.json'))
for d in glob.glob(f'{H}/mitefit/live/ext/*/meta.json'):
    m = json.load(open(d)); mid = os.path.basename(m['source']).split('.')[0]
    if mid in live: name2map[live[mid]['map']] = f'{H}/mitefit/live/ext/maps/{m["map"]["hash"]}.json'
m05 = dict(l.rstrip('\n').split('|') if '|' in l else l.rstrip('\n').split('\t') for l in open(f'{H}/mitere/raw/maps05.tsv'))
mid2name = {os.path.basename(v).split('.')[0]: k for k, v in m05.items()}
for d in glob.glob(f'{H}/mitere/ana05/*/meta.json'):
    m = json.load(open(d)); mid = os.path.basename(m['source']).split('.')[0]
    if mid in mid2name: name2map[mid2name[mid]] = f'{H}/mitere/ana05/maps/{m["map"]["hash"]}.json'
print('maps with geometry', len(name2map), file=sys.stderr)

def feats(mp, side):
    t = 0 if side == 'a' else 1
    s = mp['spawn'][t]; sp = ((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2)
    s2 = mp['spawn'][1 - t]; sp2 = ((s2['minX'] + s2['maxX']) / 2, (s2['minY'] + s2['maxY']) / 2)
    ty = collections.Counter(c['type'] for c in mp['camps'])
    gems = sum(q['gems'] for q in mp['groups']); gold = sum(q['gold'] for q in mp['groups'])
    area = mp['width'] * mp['height']
    alt = mp['altars']
    da = sorted(cheb(sp, a) for a in alt)
    dg = sorted(cheb(sp, q['tiles'][0]) for q in mp['groups'])
    big = [q for q in mp['groups'] if any(x in ('Golem', 'Monolith') for x in q['types'])]
    return {'picks': mp['champsPerTeam'], 'area': area, 'W': mp['width'], 'H': mp['height'], 'alt': len(alt),
            'gemcl': ty['Gem cluster'], 'goldcl': ty['Gold cluster'], 'wolf': ty['Wolf'], 'elk': ty['Elk'], 'golem': ty['Golem'],
            'mono': ty['Monolith'], 'groups': len(mp['groups']), 'gems': gems, 'gold': gold, 'gem_per_area': gems / area * 1000,
            'gold_gem': gold / max(1, gems), 'walls': len(mp['walls']) / area, 'holes': len(mp['holes']) / area,
            'bush': len(mp['bushes']) / area, 'spdist': cheb(sp, sp2), 'alt_near': da[0] if da else 99,
            'grp_near5': dg[min(4, len(dg) - 1)] if dg else 99, 'big': len(big),
            'sym': {'horizontal': 0, 'vertical': 1, 'rotational': 2}.get(mp['symmetry'], 3)}

tab = {}
for r in meta.rows():
    if r['ep'] >= EP and r['kind'] == 'ranked': tab[(r['map'], r['m_side'])] = tuple(meta.names(r['m_picks']))
for r in meta.rows():
    if r['ep'] >= EP and (r['map'], r['m_side']) not in tab and r['opp'] != meta.US: tab[(r['map'], r['m_side'])] = tuple(meta.names(r['m_picks']))
X, Y, K = [], [], []
for (mname, side), p in tab.items():
    if mname not in name2map: continue
    f = feats(json.load(open(name2map[mname])), side)
    X.append(f); Y.append(p); K.append((mname, side))
print('cells', len(X), 'new-map cells', sum(k[0].startswith('05') for k in K), file=sys.stderr)
cols = list(X[0])
A = np.array([[x[c] for c in cols] for x in X], dtype=float)
def label(p, kind):
    if kind == 'team': return ' '.join(sorted(p))
    if kind == 'slot1': return p[1] if len(p) == 5 and p[0] == 'Vesper' else 'other'
    if kind == 'first': return p[0]
tr = np.array([not k[0].startswith('05') for k in K]); te = ~tr
for kind in ('team', 'slot1'):
    y = np.array([label(p, kind) for p in Y])
    base = collections.Counter(y[tr]).most_common(1)[0]
    best = None
    for depth in (2, 3, 4, 5, 6, 8):
        clf = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=2, random_state=0).fit(A[tr], y[tr])
        acc_tr = (clf.predict(A[tr]) == y[tr]).mean(); acc_te = (clf.predict(A[te]) == y[te]).mean()
        print(f'{kind} depth {depth}: train {acc_tr:.3f} new-maps {acc_te:.3f} (n {te.sum()}; majority "{base[0]}" {np.mean(y[te] == base[0]):.3f})')
        if depth == 4: best = clf
    print(export_text(best, feature_names=cols, max_depth=4))
# picks-count rule: composition by number of picks on all cells
byn = collections.defaultdict(collections.Counter)
for x, p in zip(X, Y): byn[x['picks']][' '.join(p)] += 1
for n in sorted(byn): print(n, byn[n].most_common(8))
