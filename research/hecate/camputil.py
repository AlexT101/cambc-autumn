"""camputil.py BATCH_DIR: captures per group-lifetime by group composition and side, for bot 1 and bot 2."""
import json, gzip, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
AN = ROOT / "replays" / ".analysis"
batch = Path(sys.argv[1]).resolve()
idx = json.loads((AN / "index.json").read_text(encoding="utf-8"))
seen = set(); rows = []
for g in idx["games"]:
    src = Path(g["source"]); src = src if src.is_absolute() else ROOT / src
    if src.resolve().parent == batch and (g["dir"], src.stem[-2:]) not in seen:
        seen.add((g["dir"], src.stem[-2:])); rows.append((g, src.stem))
# key: (composition, side-rel-to-bot1) -> [groups, captures by bot1, captures by bot2, possible cycles]
T = collections.defaultdict(lambda: [0, 0, 0, 0.0, 0, 0])
for g, stem in rows:
    d = AN / g["dir"]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    mp = json.loads((d / meta["mapFile"]).read_text(encoding="utf-8"))
    b1 = 0 if stem.endswith("-12") else 1
    rounds = meta["result"]["rounds"]
    caps = collections.Counter()
    gems_by = collections.Counter()
    for e in (json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")):
        if e["k"] == "capture": caps[(e["g"], e["team"])] += 1
    for gr in mp["groups"]:
        if gr["gems"] == 0 and gr["gold"] == 0: continue
        comp = "+".join(sorted(collections.Counter(gr["types"]).elements())) if isinstance(gr["types"], list) else str(gr["types"])
        comp = comp.replace("Gem cluster", "gem").replace("Gold cluster", "gold").replace("Wolf", "wolf").replace("Elk", "elk").replace("Monolith", "MONO")
        side = "mid" if gr["side"] == -1 else ("own" if gr["side"] == b1 else "far")
        t = T[(comp if len(comp) < 30 else comp[:30], side)]
        t[0] += 1; t[1] += caps[(gr["id"], b1)]; t[2] += caps[(gr["id"], 1 - b1)]
        t[3] += rounds / (gr["respawn"] + 20)
        t[4] += gr["gems"]
print(f"{len(rows)} games. side is relative to bot 1 (own = nearer bot 1's spawn). util = captures / (rounds/(respawn+20))")
print(f"{'composition':32s} {'side':4s} {'groups':>6s} {'gems':>5s} {'cap1':>6s} {'cap2':>6s} {'util1':>6s} {'util2':>6s}")
for (comp, side), t in sorted(T.items(), key=lambda kv: -kv[1][0]):
    if t[0] < 20: continue
    print(f"{comp:32s} {side:4s} {t[0]:6d} {t[4]/t[0]:5.0f} {t[1]/t[0]:6.2f} {t[2]/t[0]:6.2f} {t[1]/t[3]:6.2f} {t[2]/t[3]:6.2f}")
