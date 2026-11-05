#!/usr/bin/env python3
"""Walks whose part K costs at least T: the other parts' means there. python3 wpart.py PKL K T [cut]"""
import sys, pickle
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from wan import PARTS

recs = [r for r in pickle.load(open(sys.argv[1], "rb")) if r["total"] < 10**6]
k, t = int(sys.argv[2]), int(sys.argv[3])
if len(sys.argv) > 4:
    recs = [r for r in recs if r["cut"]]
sel = [r for r in recs if r["acc"].get(k, (0, 0))[0] >= t]
print(f"{len(sel)} of {len(recs)} walks with {PARTS[k]} >= {t}; total mean {np.mean([r['total'] for r in sel]):.0f}, chunks p50 {np.median([r['chunks'] for r in sel]):.0f}")
for j, nm in PARTS.items():
    v = [r["acc"].get(j, (0, 0)) for r in sel]
    f = np.mean([x[0] for x in v])
    c = np.mean([x[1] for x in v])
    if f > 50 or (nm.startswith("#") and c):
        print(f"  {nm:22s} {f:8.0f}  calls {c:5.2f}")
