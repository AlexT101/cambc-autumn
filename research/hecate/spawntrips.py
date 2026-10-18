"""spawntrips.py BATCH_DIR: per champion visit to spawn (recall arrival or respawn): rounds until it next hits a camp
or starts a tribute, split by why it went (death / recall with bag / recall without bag)."""
import json, gzip, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
AN = ROOT / "replays" / ".analysis"
batch = Path(sys.argv[1]).resolve()
which = int(sys.argv[2]) if len(sys.argv) > 2 else 0
idx = json.loads((AN / "index.json").read_text(encoding="utf-8"))
seen = set(); rows = []
for g in idx["games"]:
    src = Path(g["source"]); src = src if src.is_absolute() else ROOT / src
    if src.resolve().parent == batch and (g["dir"], src.stem[-2:]) not in seen:
        seen.add((g["dir"], src.stem[-2:])); rows.append((g, src.stem))
S = collections.defaultdict(list); total_rounds = 0; nch = 0
for g, stem in rows:
    d = AN / g["dir"]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    team = (0 if stem.endswith("-12") else 1) ^ which
    ids = {c["id"] for c in meta["champions"] if c["team"] == team}
    nch += len(ids); total_rounds += meta["result"]["rounds"] * len(ids)
    ev = [json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")]
    pending = {}
    for e in ev:
        a = e.get("a")
        if e["k"] == "recall_end" and a in ids: pending[a] = (e["r"], "recall_bag" if e.get("gems", 0) > 0 else "recall_empty")
        elif e["k"] == "respawn" and a in ids: pending[a] = (e["r"], "respawn")
        elif a in pending and ((e["k"] in ("attack", "cast") and "camp" in e) or e["k"] == "tribute_start"):
            r0, why = pending.pop(a); S[why].append(e["r"] - r0)
n = len(rows)
print(f"{n} games; champion-rounds/game {total_rounds/n:.0f}")
for why, v in S.items(): print(f"  {why:13s} trips/game {len(v)/n:5.2f}  mean rounds to work {sum(v)/len(v):5.1f}  total/game {sum(v)/n:6.1f}")
