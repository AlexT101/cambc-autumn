"""whowins.py BATCH_DIR: winner-minus-loser differences per game (mirror analysis)."""
import json, gzip, sys, collections, statistics
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
D = collections.defaultdict(list); first_kill = collections.Counter(); margin = []
for g in rows:
    d = AN / g["dir"]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    mp = json.loads((d / meta["mapFile"]).read_text(encoding="utf-8"))
    side = {gr["id"]: gr["side"] for gr in mp["groups"]}
    w = meta["result"]["winner"]
    team = {c["id"]: c["team"] for c in meta["champions"]}
    S = collections.Counter()
    fk = None
    for e in (json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")):
        if e["k"] == "death" and not e.get("linked"):
            t = team[e["v"]]
            S[("deaths", t)] += 1; S[("baglost", t)] += e.get("gems", 0)
            if e.get("by") != "camp" and fk is None: fk = 1 - t
            if e["r"] <= 150: S[("deaths150", t)] += 1
        elif e["k"] == "capture":
            sd = side[e["g"]]
            where = "mid" if sd == -1 else ("own" if sd == e["team"] else "steal")
            for cid, gems, gold in e["shares"]:
                S[("capgems_" + where, e["team"])] += gems; S[("gold", e["team"])] += gold
                if e["r"] <= 150: S[("gems150", e["team"])] += gems
        elif e["k"] == "tribute_end":
            pass
    if fk is not None: first_kill[fk == w] += 1
    for k in {k for k, _ in S}:
        D[k].append(S[(k, w)] - S[(k, 1 - w)])
    margin.append(meta["result"]["gems"][w] - meta["result"]["gems"][1 - w])
print(f"{len(rows)} distinct games; median gem margin {statistics.median(margin)}; first kill by winner {first_kill[True]}/{sum(first_kill.values())}")
for k, v in sorted(D.items()):
    pos = sum(x > 0 for x in v); neg = sum(x < 0 for x in v)
    print(f"  {k:16s} mean diff {statistics.mean(v):7.1f}  winner more {pos:3d} / less {neg:3d}")
