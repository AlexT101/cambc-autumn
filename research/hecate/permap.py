"""permap.py RESULT_DIR [regex]: per-map wins for bot 1 (maps matching regex)."""
import json, sys, re, collections
from pathlib import Path
r = json.loads((Path(sys.argv[1]) / "results.json").read_text())
pat = re.compile(sys.argv[2]) if len(sys.argv) > 2 else None
W = collections.defaultdict(lambda: [0, 0, []])
for m in r["matches"]:
    name = Path(m["map"]).stem
    if pat and not pat.search(name): continue
    w = W[name]; w[0] += m.get("winner") == 0; w[1] += 1; w[2].append(m.get("rounds"))
tw = sum(v[0] for v in W.values()); tn = sum(v[1] for v in W.values())
for k, v in sorted(W.items()): print(f"{k:40s} {v[0]}/{v[1]} rounds {v[2]}")
print(f"total {tw}/{tn}")
