"""batchstats.py BATCH_DIR: per-batch summary from replays/.analysis (bot 1's view)."""
import json, gzip, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
AN = ROOT / "replays" / ".analysis"
batch = Path(sys.argv[1]).resolve()
idx = json.loads((AN / "index.json").read_text(encoding="utf-8"))
rows = [g for g in idx["games"] if Path(g["source"]).resolve().parent == batch] if False else []
for g in idx["games"]:
    src = Path(g["source"])
    if not src.is_absolute(): src = (ROOT / src)
    if src.resolve().parent == batch: rows.append(g)
res = json.loads((batch / "results.json").read_text(encoding="utf-8"))
S = collections.Counter()
n = 0
for g in rows:
    d = AN / g["dir"]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    stem = Path(g["source"]).stem
    b1 = 0 if stem.endswith("-12") else 1  # team index of bot 1
    n += 1
    S["rounds"] += meta["result"]["rounds"]
    S["win"] += meta["result"]["winner"] == b1
    S["gems1"] += meta["result"]["gems"][b1]; S["gems2"] += meta["result"]["gems"][1 - b1]
    for e in (json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")):
        if e["k"] == "death":
            team = next(c["team"] for c in meta["champions"] if c["id"] == e["v"])
            who = "1" if team == b1 else "2"
            if e.get("linked"): continue
            S[f"death{who}_{'camp' if e.get('by') == 'camp' else 'champ'}"] += 1
            S[f"bag_lost{who}"] += e.get("gems", 0)
        elif e["k"] == "capture":
            for cid, gems, gold in e["shares"]:
                team = next(c["team"] for c in meta["champions"] if c["id"] == cid)
                who = "1" if team == b1 else "2"
                S[f"capgems{who}"] += gems; S[f"capgold{who}"] += gold
print(f"{n} games")
for k in sorted(S): print(f"  {k:16s} {S[k]/n:8.2f}")
