"""Mean candidate win rate and score of tune runs by blocks of iterations (history.jsonl).

    py research/tune-combo3-2026-11-06/progress.py RUN... [--block 100]
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
args = sys.argv[1:]
block = 100
if "--block" in args:
    i = args.index("--block"); block = int(args[i + 1]); del args[i:i + 2]
for name in args:
    h = [json.loads(l) for l in (ROOT / "replays" / "tune" / name / "history.jsonl").read_text().splitlines()]
    out = []
    for s in range(0, len(h), block):
        b = h[s:s + block]
        win = sum(sum(r["win"].values()) / len(r["win"]) for r in b) / len(b)
        sc = sum(sum(r["mean"].values()) / len(r["mean"]) for r in b) / len(b)
        out.append(f"{b[0]['k']}-{b[-1]['k']}: {100 * win:.2f}% ({sc:+.4f})")
    print(f"{name}: " + ", ".join(out))
