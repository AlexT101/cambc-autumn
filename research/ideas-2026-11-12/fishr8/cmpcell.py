"""Matched-cell comparison: per (map, side) mean of A's games against B's, on cells both hold (B usually r8).
    py cmpcell.py A.jsonl B.jsonl [VERSION_A]"""
import json, sys, collections, math
A = [json.loads(l) for l in open(sys.argv[1])]; B = [json.loads(l) for l in open(sys.argv[2])]
va = int(sys.argv[3]) if len(sys.argv) > 3 else None
if va: A = [g for g in A if g.get('version') == va]
ca = collections.defaultdict(list); cb = collections.defaultdict(list)
for g in A: ca[(g['map'], g['side'])].append(g)
for g in B: cb[(g['map'], g['side'])].append(g)
cells = sorted(set(ca) & set(cb)); print(len(cells), 'cells')
def cm(c, side, k):
    v = [g[side].get(k) for g in c]; v = [x for x in v if isinstance(x, (int, float))]
    return sum(v) / len(v) if v else None
keys = sorted({k for g in B for k in g['m'] if isinstance(g['m'][k], (int, float))})
win = lambda c: sum(g['mite_win'] for g in c) / len(c)
wa = sum(win(ca[x]) for x in cells) / len(cells); wb = sum(win(cb[x]) for x in cells) / len(cells)
print(f'Fish win  A {wa:.3f}  B {wb:.3f}')
for side in 'mo':
    for k in keys:
        d = [(cm(ca[x], side, k), cm(cb[x], side, k)) for x in cells]; d = [(a, b) for a, b in d if a is not None and b is not None]
        if len(d) < 5: continue
        a = sum(p for p, _ in d) / len(d); b = sum(q for _, q in d) / len(d)
        diffs = [q - p for p, q in d]; m = sum(diffs) / len(d); sd = math.sqrt(sum((x - m) ** 2 for x in diffs) / max(1, len(d) - 1)) / math.sqrt(len(d))
        print(f'{side} {k:20s} {a:10.2f} {b:10.2f}   diff {m:+9.2f} (z {m / sd if sd else 0:+5.1f})')
