# KS on every scalar metric stats.mjs writes (not only compare.py's list), ladder against each generated set.
#   python3 research/ideas-2026-11-12/ladderv3/ksall.py ladder=ladder170.jsonl v3=v3.jsonl v4=v4.jsonl
import json, sys, numpy as np
from scipy import stats
S = {a.split('=', 1)[0]: [json.loads(l) for l in open(a.split('=', 1)[1]) if l.strip()] for a in sys.argv[1:]}
ref, oth = list(S)[0], list(S)[1:]
keys = [k for k, v in S[ref][0]['f'].items() if not k.startswith(('sq_', 'pr_')) and not isinstance(v, (dict, list))]
val = lambda R, k: np.array([-1.0 if r['f'][k] is None else float(r['f'][k]) for r in R])
q = lambda x: '/'.join(f'{np.percentile(x, p):.3g}' for p in (10, 50, 90))
rows = []
for k in keys:
    l = val(S[ref], k); t = [stats.ks_2samp(l, val(S[o], k)) for o in oth]
    rows.append((t[-1].pvalue, k, [q(l)] + [q(val(S[o], k)) for o in oth], t))
rows.sort()
print(f'Sets: ' + ', '.join(f'{n} {len(R)}' for n, R in S.items()) + f'; {len(keys)} metrics\n')
for o, i in zip(oth, range(len(oth))):
    ps = [r[3][i].pvalue for r in rows]
    print(f'- {o}: p < 0.01 on {sum(p < 0.01 for p in ps)}, p < 0.05 on {sum(p < 0.05 for p in ps)}, mean D {np.mean([r[3][i].statistic for r in rows]):.3f}')
print('\n| metric | ' + ' | '.join(f'{n} p10/50/90' for n in S) + ' | ' + ' | '.join(f'{o} D (p)' for o in oth) + ' |')
print('|---|' + '---|' * (len(S) + len(oth)))
for p, k, qs, t in rows: print(f'| {k} | ' + ' | '.join(qs) + ' | ' + ' | '.join(f'{x.statistic:.3f} ({x.pvalue:.1e})' for x in t) + ' |')
