# compare.py CVDIR [BASESET]: each set's CV log loss against the base set: mean change, fold-to-fold SE, map-clustered SE.
import json, sys, glob, re, math
import numpy as np

d = sys.argv[1]
base_i = int(sys.argv[2]) if len(sys.argv) > 2 else 0
sets = {int(re.search(r'set(\d+)', f).group(1)): json.load(open(f)) for f in glob.glob(f'{d}/set*.json')}
b = sets[base_i]
keys = sorted(b['perMap'])
bn = np.array([b['perMap'][k][0] for k in keys]); bl = np.array([b['perMap'][k][1] for k in keys])
N = bn.sum()
basef = b['features']
print(f'base set {base_i}: cv {b["total"]:.6f}; {len(keys)} maps, {N} games')
alt = {}
for l in open('/home/ubuntu/cambc-autumn/replays/draftlab/draft5/maps.jsonl'):
    m = json.loads(l); alt[m['key']] = (min(m['f']['altars'], 6), m['set'] == 'maps')
# Ladder-mix weights per altar bin (the fresh df-9911xx pool: 1, 2, 3, 4, 5, 6+ altars).
fresh = {1: 477, 2: 838, 3: 201, 4: 324, 5: 56, 6: 151}
abin = np.array([alt[k][0] for k in keys]); lad = np.array([alt[k][1] for k in keys])
wbin = {a: fresh[a] / sum(fresh.values()) / bn[abin == a].sum() for a in fresh}
wmap = np.array([wbin[a] for a in abin]) * N  # per-game weight so the total weight is N
def sub(mask, dm, w=None):
    w = np.ones(len(dm)) if w is None else w
    W = (bn * w)[mask].sum()
    x = (dm * w)[mask]
    return 1e4 * x.sum() / W, 1e4 * math.sqrt(mask.sum()) * x.std(ddof=1) / W
print('set | added | cv | change x1e4 | fold SE x1e4 | map SE x1e4 | folds better | picks change x1e4 (3/4/5) | one-altar maps | reweighted to ladder-mix altars | ladder maps')
for i in sorted(sets):
    s = sets[i]
    added = [f for f in s['features'] if f not in basef]
    removed = [f for f in basef if f not in s['features']]
    lab = (','.join(added) if len(added) < 4 else f'{added[0]}..+{len(added)}') + (' -' + ','.join(removed) if removed else '')
    if s['lam'] != b['lam']: lab += ' lam' + json.dumps({k: v for k, v in s['lam'].items() if b['lam'][k] != v})
    fd = np.array([f['loss'] - g['loss'] for f, g in zip(s['folds'], b['folds'])])
    sl = np.array([s['perMap'][k][1] for k in keys])
    dm = sl - bl
    mse = math.sqrt(len(keys)) * dm.std(ddof=1) / N
    pk = ' / '.join(f'{1e4 * (s["perPick"][p] - b["perPick"][p]):+.2f}' for p in ('3', '4', '5'))
    oa, oas = sub(abin == 1, dm); lw, lws = sub(abin > 0, dm, wmap); ld, lds = sub(lad, dm)
    print(f'{i} | {lab or "base"} | {s["total"]:.6f} | {1e4 * (s["total"] - b["total"]):+.2f} | {1e4 * fd.std(ddof=1) / math.sqrt(5):.2f} | {1e4 * mse:.2f} | {(fd < 0).sum()}/5 | {pk} | one-altar {oa:+.2f} ±{oas:.2f} | ladder-mix weighted {lw:+.2f} ±{lws:.2f} | ladder126 {ld:+.2f} ±{lds:.2f}')
