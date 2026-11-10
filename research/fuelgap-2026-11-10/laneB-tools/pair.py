#!/usr/bin/env python3
"""Pair two ab.py logs on the same suite by map: mean per-map difference of bot 1's score, 95% CI, share of games changed."""
import re, sys, math
pat = re.compile(r'\] (\S+) A=(\d) B=(\d): (bot (\d) wins|draw)')
def load(p):
    out = {}
    for line in open(p):
        m = pat.search(line)
        if not m: continue
        mp, a = m.group(1), m.group(2)
        sc = 0.5 if m.group(4) == 'draw' else (1.0 if m.group(5) == '1' else 0.0)
        out[(mp, a)] = sc
    return out
x, y = load(sys.argv[1]), load(sys.argv[2])
keys = sorted(set(x) & set(y))
maps = sorted({k[0] for k in keys})
d = []
for mp in maps:
    ks = [k for k in keys if k[0] == mp]
    if len(ks) != 2: continue
    d.append(sum(x[k] - y[k] for k in ks) / 2)
n = len(d); m = sum(d) / n; v = sum((t - m) ** 2 for t in d) / (n - 1)
changed = sum(x[k] != y[k] for k in keys) / len(keys)
print(f"games {len(keys)} maps {n}: {sum(x[k] for k in keys)/len(keys)*100:.2f} vs {sum(y[k] for k in keys)/len(keys)*100:.2f}; paired {m*100:+.2f} +-{1.96*math.sqrt(v/n)*100:.2f}; changed {changed*100:.0f}%")
