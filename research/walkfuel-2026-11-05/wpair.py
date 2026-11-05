#!/usr/bin/env python3
"""Paired walks of two WLK runs of identical games (100M): python3 wpair.py BASE.pkl CAND.pkl"""
import sys, pickle, collections
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from wan import PARTS


def keyed(path):
    recs = pickle.load(open(path, "rb"))
    seq = collections.Counter()
    out = {}
    for r in recs:
        k = (r["map"], r["round"], r["handle"])
        out[k + (seq[k],)] = r
        seq[k] += 1
    return out


a, b = keyed(sys.argv[1]), keyed(sys.argv[2])
common = [k for k in a if k in b and a[k]["entry"] == b[k]["entry"] and a[k]["total"] < 10**6 and b[k]["total"] < 10**6]
print(f"{len(a)} / {len(b)} walks, {len(common)} paired")
ta = np.array([a[k]["total"] for k in common], dtype=float)
tb = np.array([b[k]["total"] for k in common], dtype=float)
print(f"total mean {ta.mean():.0f} -> {tb.mean():.0f} ({tb.mean()/ta.mean()-1:+.1%}); p50 {np.percentile(ta,50):.0f} -> {np.percentile(tb,50):.0f}; "
      f"p90 {np.percentile(ta,90):.0f} -> {np.percentile(tb,90):.0f}; p99 {np.percentile(ta,99):.0f} -> {np.percentile(tb,99):.0f}")
# Per turn.
turn_a, turn_b = collections.Counter(), collections.Counter()
for k in common:
    turn_a[k[:3]] += a[k]["total"]
    turn_b[k[:3]] += b[k]["total"]
xa = np.array(list(turn_a.values()), dtype=float)
xb = np.array([turn_b[k] for k in turn_a], dtype=float)
print(f"per turn mean {xa.mean():.0f} -> {xb.mean():.0f} ({xb.mean()/xa.mean()-1:+.1%}); p90 {np.percentile(xa,90):.0f} -> {np.percentile(xb,90):.0f}; "
      f"p99 {np.percentile(xa,99):.0f} -> {np.percentile(xb,99):.0f}; p99.9 {np.percentile(xa,99.9):.0f} -> {np.percentile(xb,99.9):.0f}")
print(f"   {'part':22s} {'base/walk':>9s} {'cand/walk':>9s} {'base/call':>9s} {'cand/call':>9s}")
for j, nm in PARTS.items():
    fa = sum(a[k]["acc"].get(j, (0, 0))[0] for k in common)
    fb = sum(b[k]["acc"].get(j, (0, 0))[0] for k in common)
    ca = sum(a[k]["acc"].get(j, (0, 0))[1] for k in common)
    cb = sum(b[k]["acc"].get(j, (0, 0))[1] for k in common)
    if ca or cb:
        print(f"   {nm:22s} {fa/len(common):9.0f} {fb/len(common):9.0f} {fa/max(ca,1):9.0f} {fb/max(cb,1):9.0f}")
