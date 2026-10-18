"""divergence.py BATCH_DIR: first round where a mirror game's team states stop being mirror images, and what differs."""
import json, gzip, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
AN = ROOT / "replays" / ".analysis"
batch = Path(sys.argv[1]).resolve()
idx = json.loads((AN / "index.json").read_text(encoding="utf-8"))
seen = set(); rows = []
for g in idx["games"]:
    src = Path(g["source"]); src = src if src.is_absolute() else ROOT / src
    if src.resolve().parent == batch and g["dir"] not in seen:
        seen.add(g["dir"]); rows.append(g)
def mirror(sym, W, H, x, y):
    if sym == "horizontal": return (W - 1 - x, y)
    if sym == "vertical": return (x, H - 1 - y)
    return (W - 1 - x, H - 1 - y)
C = collections.Counter(); first = []
for g in rows:
    d = AN / g["dir"]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    W, H, sym = meta["map"]["width"], meta["map"]["height"], meta["map"]["symmetry"]
    R = json.load(gzip.open(d / "rounds.json.gz"))
    A = [c for c in R["champions"] if c["team"] == 0]; B = [c for c in R["champions"] if c["team"] == 1]
    div = None
    for i, r in enumerate(R["round"]):
        for a, b in zip(A, B):
            if a["alive"][i] != b["alive"][i]: div = (r, "alive"); break
            if not a["alive"][i]: continue
            if mirror(sym, W, H, a["x"][i], a["y"][i]) != (b["x"][i], b["y"][i]): div = (r, "pos"); break
            if abs(a["hp"][i] - b["hp"][i]) > 0.01: div = (r, "hp"); break
            if a["gems"][i] != b["gems"][i]: div = (r, "gems"); break
        if div: break
    w = meta["result"]["winner"]
    first.append((div[0] if div else None, div[1] if div else None, w, meta["map"]["name"]))
rs = sorted(x[0] for x in first if x[0])
print(len(first), "games; first divergence round quartiles", rs[len(rs)//4], rs[len(rs)//2], rs[3*len(rs)//4])
print(collections.Counter(x[1] for x in first))
for lo, hi in [(0, 5), (5, 20), (20, 60), (60, 10**9)]:
    sub = [x for x in first if x[0] and lo <= x[0] < hi]
    print(f"diverge r{lo}-{hi}: {len(sub)} games, A wins {sum(x[2]==0 for x in sub)}")
