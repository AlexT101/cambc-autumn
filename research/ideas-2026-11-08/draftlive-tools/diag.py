import sys, numpy as np, collections, json
sys.path.insert(0, '/home/ubuntu/tmp-offload/draftlive/scripts'); import load
R = load.rows(sys.argv[1])
F92 = {m['name']: m for m in json.load(open(load.W / 'f92scores.json'))}
ctrl = {(r['map'], r['side'], r['opp']): r['win'] for r in R if r['k'] == -1}
k0 = {(r['map'], r['side'], r['opp']): r['win'] for r in R if r['k'] == 0}
print('control k=-1 vs k=0 agree', sum(ctrl[c] == k0.get(c) for c in ctrl), '/', len(ctrl), 'ctrl win', np.mean(list(ctrl.values())).round(3), 'k0', np.mean(list(k0.values())).round(3))
R = [r for r in R if r['k'] >= 0]
# within-cell slope of win on s, simple linear probability by subgroup (centred per cell)
def slope(sub):
    by = collections.defaultdict(list)
    for r in sub: by[(r['map'], r['side'], r['opp'])].append(r)
    xs, ys = [], []
    for v in by.values():
        ms = np.mean([r['s'] for r in v]); mw = np.mean([r['win'] for r in v])
        xs += [r['s'] - ms for r in v]; ys += [r['win'] - mw for r in v]
    xs, ys = np.array(xs), np.array(ys); b = (xs @ ys) / (xs @ xs); e = ys - b * xs
    return b, np.sqrt((e @ e) / (xs @ xs) / len(xs)) * np.sqrt(len(xs))
print('win-pts per F92 logit (linear, within cell); F92 implies ~25 near 50%')
for name, f in [('all', lambda r: True), ('F', lambda r: r['opp'] == 'F'), ('M', lambda r: r['opp'] == 'M'),
                ('3 picks', lambda r: r['picks'] == 3), ('4 picks', lambda r: r['picks'] == 4), ('5 picks', lambda r: r['picks'] == 5),
                ('one altar', lambda r: F92[r['map']]['z'][30] > 0), ('multi altar', lambda r: F92[r['map']]['z'][30] <= 0),
                ('top40 only', lambda r: r['k'] < 40)]:
    sub = [r for r in R if f(r)]; b, se = slope(sub); print(f'  {name:12s} n {len(sub):6d}  {b * 100:5.1f} ±{se * 100:.1f}')
# base team rank among top 40 per map (realized mean over 4 cells)
by = collections.defaultdict(list)
for r in R: by[(r['map'], r['k'])].append(r['win'])
gaps = []
for m in F92:
    top = [np.mean(by[(m, k)]) for k in range(40) if by[(m, k)]]
    gaps.append(top[0] - np.mean(top[1:]))
print('base team minus mean of F92 ranks 2-40, per map (4 games each):', np.mean(gaps).round(3), '±', (np.std(gaps) / np.sqrt(len(gaps))).round(3))
