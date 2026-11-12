"""Fish ('m') and our ('o') per-game means, two or more stats files side by side (mstats/fstats output).
    py cmp.py A.jsonl B.jsonl ... [--keys k1,k2]"""
import json, sys, collections, math
files = [a for a in sys.argv[1:] if not a.startswith('--')]
D = [[json.loads(l) for l in open(f)] for f in files]
keys = sorted({k for d in D for g in d for k in g['m'] if isinstance(g['m'][k], (int, float))})
print(f'{"stat":24s}' + ''.join(f'{f.split("/")[-1][:20]:>22s}' for f in files))
print(f'{"games / Fish win":24s}' + ''.join(f'{len(d):>10d} {sum(1 for g in d if g["mite_win"])/len(d):>11.3f}' for d in D))
for side in 'mo':
    for k in keys:
        row = []
        for d in D:
            v = [g[side].get(k) for g in d]; v = [x for x in v if isinstance(x, (int, float))]
            row.append(sum(v) / len(d) if k in ('kills', 'deaths') else (sum(v) / len(v) if v else float('nan')))
        print(f'{side} {k:22s}' + ''.join(f'{x:>22.3f}' for x in row))
