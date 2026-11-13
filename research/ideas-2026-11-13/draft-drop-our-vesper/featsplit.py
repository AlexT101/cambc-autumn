import json, math, sys
rows = {r['map']: r for r in json.load(open(sys.argv[1]))}
F = {}
for l in open('feat-b01.jsonl'):
    r = json.loads(l); F[r['name']] = r['f']
def est(v):
    n = len(v); m = sum(v) / n; sd = math.sqrt(sum((a - m) ** 2 for a in v) / (n - 1))
    return f'{100*m:+.2f} ±{196*sd/math.sqrt(n):.2f} (n {n})'
s = [r for m, r in rows.items() if m in F and r['refV']]
for feat, cuts in (('gems_side', [100, 140, 200, 300]), ('gold_side', [400, 700, 1000]), ('area', [2000, 4000, 7000]), ('picks', None), ('altars', [2, 3, 5])):
    print(feat)
    if feat == 'picks':
        for p in (3, 4, 5):
            v = [r for r in s if len(r['ref']) == p]
            print(f'   picks {p}: all {est([r["all"] for r in v])}  F {est([r["F"] for r in v])}  M {est([r["M"] for r in v])}')
        continue
    edges = [-1e9] + cuts + [1e9]
    for lo, hi in zip(edges, edges[1:]):
        v = [r for r in s if lo <= (F[r['map']].get(feat) or 0) < hi]
        if len(v) > 30: print(f'   [{lo:g},{hi:g}): all {est([r["all"] for r in v])}  F {est([r["F"] for r in v])}  M {est([r["M"] for r in v])}')
