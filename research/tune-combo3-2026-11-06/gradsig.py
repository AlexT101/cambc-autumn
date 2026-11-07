"""Per-constant SPSA gradient signal of a tune run, from games.jsonl: each iteration's gradient estimate per constant
(mean over its sign pairs of the paired score difference / (2 c_i delta_i)), then its mean and t over iterations, and
the move so far in the constant's own units.

    py research/tune-combo3-2026-11-06/gradsig.py RUN [FROM_ITER]
"""
import json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
run = ROOT / "replays" / "tune" / sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
cfg = json.loads((run / "config.json").read_text())
st = json.loads((run / "state.json").read_text())
spec = json.loads((run / "base" / "src" / "tune.json").read_text())
default = dict(spec["floats"] + spec["ints"])
g = {}
for line in (run / "games.jsonl").read_text().splitlines():
    r = json.loads(line)
    if r["k"] < start:
        continue
    names, sc = r["names"], r["scores"]
    est = [0.0] * len(names)
    for p, d in enumerate(r["deltas"]):
        a, b = sc[f"p{p}"], sc[f"m{p}"]
        both = [i for i in range(len(a)) if a[i] is not None and b[i] is not None]
        diff = sum(a[i] - b[i] for i in both) / max(1, len(both))
        for j in range(len(names)):
            est[j] += diff / (2 * r["cn"][j] * d[j]) / len(r["deltas"])
    for j, n in enumerate(names):
        g.setdefault(n, []).append(est[j])
rows = []
for n, v in g.items():
    m = sum(v) / len(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / max(1, len(v) - 1))
    lo, hi, kind = cfg["params"][n]
    now = lo + min(1, max(0, st["x"][n])) * (hi - lo)
    rows.append((m / (sd / math.sqrt(len(v))) if sd > 0 else 0.0, n, default[n], now, len(v)))
rows.sort(key=lambda r: -abs(r[0]))
print(f"{run.name}: iteration {st['k']}, gradients from iteration {start}")
for t, n, d, now, k in rows:
    print(f"  {n:30s} t {t:+6.2f}   {d:10.4f} -> {now:10.4f} ({100 * (now - d) / d if d else 0:+6.1f}%)")
