"""stealops.py BATCH_DIR: capture holds with an opposing champion near, and their outcomes."""
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
C = collections.Counter()
for g in rows:
    d = AN / g["dir"]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    mp = json.loads((d / meta["mapFile"]).read_text(encoding="utf-8"))
    gems = {gr["id"]: gr["gems"] for gr in mp["groups"]}
    tiles = {gr["id"]: [tuple(t) for t in gr["tiles"]] for gr in mp["groups"]}
    R = json.load(gzip.open(d / "rounds.json.gz"))
    ri = {r: i for i, r in enumerate(R["round"])}
    team = {c["id"]: c["team"] for c in meta["champions"]}
    ev = [json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")]
    for e in ev:
        if e["k"] == "group_clear":
            gid = e["g"]; r = e["r"]; i = ri.get(r)
            if i is None or gems.get(gid, 0) == 0: continue
            # who is on/near: holders = champions within 1 of tiles; opponents within 8
            near = collections.defaultdict(list)
            for c in R["champions"]:
                if not c["alive"][i] or c["x"][i] is None: continue
                dmin = min(max(abs(c["x"][i] - x), abs(c["y"][i] - y)) for x, y in tiles[gid])
                near[team[c["id"]]].append((dmin, c["hp"][i] / c["maxHp"][i]))
            for t in (0, 1):
                mine = [x for x in near[t] if x[0] <= 1]
                opp = [x for x in near[1 - t] if x[0] <= 8]
                if mine and opp and not [x for x in near[1 - t] if x[0] <= 1]:
                    C["clears_with_opp_within8"] += 1
                    C[f"opp_count={min(len(opp),3)} vs mine={min(len(mine),3)}"] += 1
                    if min(h for _, h in mine) < 0.5: C["clearer_below_half_hp"] += 1
            C["clears"] += 1
        if e["k"] == "capture_reset" and e.get("contested"): C["contested_resets"] += 1
        if e["k"] == "capture_flip": C["flips"] += 1
print(len(rows), "games")
for k, v in sorted(C.items()): print(f"  {k:32s} {v:6d}  per game {v/len(rows):.2f}")
