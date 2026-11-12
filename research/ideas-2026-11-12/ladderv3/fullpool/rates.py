#!/usr/bin/env python3
# rates.py SET.jsonl...: per part (128 / 05 / all) the fitted rates against the ladder parts, and KS on every metric.
import json, sys, numpy as np
from scipy import stats
S = '/home/ubuntu/tmp-offload/ladderv3/stats/'
load = lambda f: [json.loads(l) for l in open(f) if l.strip()]
LAD = {'128': load(S + 'old128.jsonl'), '05': load(S + 'new05.jsonl'), 'all': load(S + 'ladder170.jsonl')}
is05 = lambda r: '-ladder05-' in r['path'] or '/mut-05' in r['path'] or r['path'].split('/')[-1].startswith('mut-05')
def part(R, p): return R if p == 'all' else [r for r in R if is05(r) == (p == '05')]
def v(R, k): return np.array([(-1 if r['f'][k] is None else float(r['f'][k])) for r in R])
def rates(R):
    fe, sr = v(R, 'fill_edge'), v(R, 'spawn_rel')
    return f'fe==1 {(fe >= 1).mean():.3f} fe<.5 {(fe < .5).mean():.3f} | sr<.5 {(sr < .5).mean():.3f} sr<.7 {(sr < .7).mean():.3f} | n {len(R)}'
SETS = {f.split('/')[-1].replace('.jsonl', ''): load(f) for f in sys.argv[1:]}
for p in ['128', '05', 'all']:
    print(f'[{p}] ladder   {rates(LAD[p])}')
    for n, R in SETS.items(): print(f'[{p}] {n:8s} {rates(part(R, p))}')
keys = [k for k, x in LAD['all'][0]['f'].items() if not k.startswith(('sq_', 'pr_')) and not isinstance(x, (dict, list))]
for n, R in SETS.items():
    for p in ['all', '05']:
        res = sorted((stats.ks_2samp(v(LAD[p], k), v(part(R, p), k)).pvalue, k) for k in keys)
        print(f'{n} vs ladder[{p}]: p<0.01 {sum(q < 0.01 for q, _ in res)}, p<0.05 {sum(q < 0.05 for q, _ in res)}; lowest', ', '.join(f'{k} {q:.1e}' for q, k in res[:6]))
