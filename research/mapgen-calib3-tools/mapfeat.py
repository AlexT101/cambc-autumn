# Ladder against generated sets: per-metric summaries, tests and histograms as JSON (for the mapfeat page, 2026-11-08).
#   python3 research/mapgen-calib3-tools/mapfeat.py --out stats.json ladder=L.jsonl v2=V2.jsonl v1=V1.jsonl \
#       [--shapes ladder=L.shapes,v2=...]   (stats.mjs rows; shapes.mjs output)
# Reuses compare.py's derive(). Numeric: two-sample KS. Shares: binomial test of the ladder's count at the generated
# rate. Categorical: chi-square goodness of fit of the ladder's counts to the generated shares, ordered bins merged
# until every expected count is 5 or more.
import contextlib, io, json, os, re, runpy, sys
import numpy as np
from scipy import stats

argv = sys.argv[1:]
out = argv[argv.index('--out') + 1]
shapes_arg = argv[argv.index('--shapes') + 1] if '--shapes' in argv else ''
sets = [a for a in argv if '=' in a and not a.startswith('--') and a != shapes_arg]
here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['compare.py', *sets]
with contextlib.redirect_stdout(io.StringIO()):
    G = runpy.run_path(os.path.join(here, 'compare.py'))
SETS, D = G['SETS'], G['D']
names = list(SETS)
REF = names[0]
EXTRA = ['choke', 'choke_rel', 'openness', 'altar_centre', 'altar_near', 'camp_near', 'contested_share', 'dash_short',
         'narrow', 'leaky', 'max_group']


def summ(a):
    a = np.asarray(a, float)
    return {'n': len(a), 'mean': a.mean(), 'median': np.median(a), 'p10': np.quantile(a, .1), 'p25': np.quantile(a, .25),
            'p75': np.quantile(a, .75), 'p90': np.quantile(a, .9), 'min': a.min(), 'max': a.max()}


def numeric_vals(s, k):
    if k in EXTRA: return [r['f'][k] for r in SETS[s] if r['f'].get(k) is not None]
    return [x[0][k] for x in D[s] if x[0][k] is not None]


res = {'sets': {s: len(SETS[s]) for s in names}, 'ref': REF, 'numeric': {}, 'shares': {}, 'categorical': {}, 'hist': {}}
for k in list(D[REF][0][0]) + EXTRA:
    row = {s: summ(numeric_vals(s, k)) for s in names}
    for o in names[1:]:
        t = stats.ks_2samp(numeric_vals(REF, k), numeric_vals(o, k)); row[f'ks_{o}'] = {'D': t.statistic, 'p': t.pvalue}
    res['numeric'][k] = row
n = len(D[REF])
for k in D[REF][0][1]:
    kref = int(sum(x[1][k] for x in D[REF])); row = {s: float(np.mean([x[1][k] for x in D[s]])) for s in names}
    for o in names[1:]:
        p = row[o]
        row[f'p_{o}'] = stats.binomtest(kref, n, p).pvalue if 0 < p < 1 else float((p == 0 and kref == 0) or (p == 1 and kref == n))
    res['shares'][k] = row


def chi(obs, exp_share):
    obs, exp = list(obs), [e * sum(obs) for e in exp_share]
    mo, me, co, ce = [], [], 0, 0
    for o_, e_ in zip(obs, exp):
        co += o_; ce += e_
        if ce >= 5: mo.append(co); me.append(ce); co = ce = 0
    if ce or co:
        if mo: mo[-1] += co; me[-1] += ce
        else: mo, me = [co], [ce]
    if len(mo) < 2: return 1.0
    return float(stats.chisquare(mo, me).pvalue)


def categorical(name, labels, key):
    cnt = {s: [sum(key(r, d) == l for r, d in zip(SETS[s], D[s])) for l in labels] for s in names}
    row = {'labels': [str(l) for l in labels], **{s: [c / len(SETS[s]) for c in cnt[s]] for s in names}, 'counts': cnt}
    for o in names[1:]:
        row[f'p_{o}'] = chi(cnt[REF], [c / len(SETS[o]) for c in cnt[o]])
    res['categorical'][name] = row


cap = lambda v, lo, hi: max(lo, min(hi, v))
categorical('altar tiles', [1, 2, 3, 4, 5, '6+'], lambda r, d: r['f']['altars'] if r['f']['altars'] < 6 else '6+')
categorical('symmetry', ['rotational', 'horizontal', 'vertical'], lambda r, d: r['sym'])
categorical('picks', [3, 4, 5], lambda r, d: r['picks'])
categorical('spawn shape', ['3x3', '4x4', '4x3', '5x2', '8x2'], lambda r, d: r['spawn_wh'])
categorical('groups per side', ['<=5', 6, 7, 8, 9, 10, 11, 12, '13+'],
            lambda r, d: '<=5' if r['f']['groups_side'] <= 5 else '13+' if r['f']['groups_side'] >= 13 else r['f']['groups_side'])
categorical('shared groups', [0, 1, 2, '3+'], lambda r, d: r['f']['shared_groups'] if r['f']['shared_groups'] < 3 else '3+')
categorical('gem balls per side', [0, 1, 2, '3+'], lambda r, d: min(3, int(d[0]['gem balls per side'])) if d[0]['gem balls per side'] < 3 else '3+')

# Group sizes, pooled over groups (not independent within a map, so the test is optimistic).
SZ = [1, 2, 3, 4, 5, 6, '7+']
gs = {s: [sum(1 for x in D[s] for z in x[2] if (z if z < 7 else '7+') == l) for l in SZ] for s in names}
row = {'labels': [str(l) for l in SZ], **{s: [c / sum(gs[s]) for c in gs[s]] for s in names}, 'counts': gs, 'pooled': True}
for o in names[1:]: row[f'p_{o}'] = chi(gs[REF], [c / sum(gs[o]) for c in gs[o]])
res['categorical']['group sizes (all groups)'] = row


def hist(name, f, edges, labels):
    h = {'labels': labels}
    for s in names:
        v = np.array([f(r, d) for r, d in zip(SETS[s], D[s])], float)
        h[s] = list(np.histogram(np.clip(v, edges[0], edges[-1] - 1e-9), edges)[0] / len(v))
    res['hist'][name] = h


altar_edges = list(range(1, 11)) + [1000]
hist('altar tiles', lambda r, d: r['f']['altars'], altar_edges, [str(i) for i in range(1, 10)] + ['10+'])
hist('groups per side', lambda r, d: r['f']['groups_side'], list(range(2, 21)) + [1000], [str(i) for i in range(2, 20)] + ['20+'])
hist('camps per side', lambda r, d: r['f']['camps_side'], list(range(0, 80, 5)) + [1000], [f'{i}-{i + 4}' for i in range(0, 75, 5)] + ['75+'])
hist('gems per side', lambda r, d: r['f']['gems_side'], list(range(0, 650, 50)) + [10 ** 6], [f'{i}-{i + 49}' for i in range(0, 600, 50)] + ['600+'])
hist('gold per side', lambda r, d: r['f']['gold_side'], list(range(0, 2100, 150)) + [10 ** 6], [f'{i}-{i + 149}' for i in range(0, 1950, 150)] + ['1950+'])
hist('long side', lambda r, d: max(r['W'], r['H']), list(range(25, 105, 5)), [f'{i}-{i + 4}' for i in range(25, 100, 5)])
hist('area', lambda r, d: r['f']['area'], list(range(0, 11000, 1000)), [f'{i // 1000}k-{i // 1000 + 1}k' for i in range(0, 10000, 1000)])
hist('spawn walk distance', lambda r, d: r['f']['spawn_dist'], list(range(0, 210, 10)) + [10 ** 6], [f'{i}-{i + 9}' for i in range(0, 200, 10)] + ['200+'])
hist('choke', lambda r, d: r['f']['choke'], list(range(0, 66, 5)) + [10 ** 6], [f'{i}-{i + 4}' for i in range(0, 65, 5)] + ['65+'])

# Group shapes (team A's 3-9 cell groups, canonical under the 8 symmetries) from shapes.mjs.
if shapes_arg:
    sh = {}
    for item in shapes_arg.split(','):
        s, f = item.split('=', 1); cur = None
        for line in open(f):
            m = re.match(r'n=(\d+) \((\d+)\)', line)
            if m: cur = m.group(1); sh.setdefault(cur, {})[s] = {'total': int(m.group(2)), 'shapes': {}}; continue
            m = re.match(r'\s+(\S+)\s+(\d+)%', line)
            if m and cur: sh[cur][s]['shapes'][m.group(1)] = int(m.group(2)) / 100
    # Commonest ladder shape per size: binomial test of the ladder's count at the generated share (groups pooled).
    for nn, v in sh.items():
        top = max(v[REF]['shapes'], key=v[REF]['shapes'].get); v['top'] = top
        k = round(v[REF]['shapes'][top] * v[REF]['total'])
        for o in names[1:]:
            if o in v: v[f'p_{o}'] = stats.binomtest(k, v[REF]['total'], min(max(v[o]['shapes'].get(top, 0), 1e-6), 1 - 1e-6)).pvalue
    res['shapes'] = sh

with open(out, 'w') as fh: json.dump(res, fh, indent=1, default=float)
print(f'{out}: ' + ', '.join(f'{s} {len(SETS[s])}' for s in names))
for kind in ('numeric', 'shares', 'categorical'):
    for o in names[1:]:
        ps = [(v[f'ks_{o}']['p'] if kind == 'numeric' else v[f'p_{o}'], k) for k, v in res[kind].items()]
        print(f'{kind} {o}: {len(ps)} tests, p<0.01: {[k for p, k in ps if p < .01]}, p<0.05: {[k for p, k in ps if .01 <= p < .05]}')
