"""holdcasts.py BATCH_DIR [0|1]: casters standing on a cleared group's capture tiles with a damage spell ready and a
live camp of another group within 4: per game, split by whether that camp's attacking members are all more
than 3 away (free damage) and whether the group is asleep."""
import json, gzip, sys, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AN = ROOT / "replays" / ".analysis"
SLOTS = {"Cassi": (0,), "Stellar": (0, 1), "Ryth": (0,), "Tavi": (1,), "Ren": (0,), "Prism": (0, 1), "Marcella": (1,)}
STR = {"Wolf": 20, "Elk": 60, "Gem cluster": 0, "Gold cluster": 0, "Monolith": 200}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


batch = Path(sys.argv[1]).resolve()
which = int(sys.argv[2]) if len(sys.argv) > 2 else 0
idx = json.loads((AN / "index.json").read_text(encoding="utf-8"))
C = collections.Counter(); n = 0
for g in idx["games"]:
    src = Path(g["source"]); src = src if src.is_absolute() else ROOT / src
    if src.resolve().parent != batch: continue
    team = (0 if src.stem.endswith("-12") else 1) ^ which
    n += 1
    d = AN / g["dir"]; meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    mp = json.loads((d / meta["mapFile"]).resolve().read_text(encoding="utf-8"))
    camps = {c["id"]: c for c in mp["camps"]}
    gc = collections.defaultdict(list)
    for c in mp["camps"]: gc[c["group"]].append(c["id"])
    tiles = {}
    for gg in mp["groups"]:
        for t in gg["tiles"]: tiles[tuple(t)] = gg["id"]
    R = json.load(gzip.open(d / "rounds.json.gz"))
    ev = sorted((json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")), key=lambda e: e["s"])
    alive = set(camps); at = {}; ei = 0
    for r in R["round"]:
        while ei < len(ev) and ev[ei]["r"] <= r:
            e = ev[ei]
            if e["k"] == "camp_death": alive.discard(e["camp"])
            elif e["k"] == "group_respawn": alive.update(gc[e["g"]])
            ei += 1
        at[r] = frozenset(alive)
    names = {c["id"]: c["name"] for c in meta["champions"]}
    for c in R["champions"]:
        if c["team"] != team or names[c["id"]] not in SLOTS: continue
        nm = names[c["id"]]
        for i in range(1, len(R["round"])):
            if not c["alive"][i] or c["turn"][i] not in (1, 2): continue
            p = (c["x"][i], c["y"][i])
            if p != (c["x"][i - 1], c["y"][i - 1]) or p not in tiles: continue
            gid = tiles[p]
            if any(cid in at[R["round"][i - 1]] for cid in gc[gid]): continue  # group not cleared
            if not any(c["cd%d" % s][i - 1] == 0 for s in SLOTS[nm]): continue
            near = [cid for cid in at[R["round"][i - 1]] if camps[cid]["group"] != gid and cheb(p, (camps[cid]["x"], camps[cid]["y"])) <= 4]
            if not near: continue
            groups = {camps[cid]["group"] for cid in near}
            free = all(cheb(p, (camps[cid]["x"], camps[cid]["y"])) > 3 for gg in groups for cid in gc[gg] if cid in at[R["round"][i - 1]] and STR[camps[cid]["type"]] > 0)
            C[(nm, "free" if free else "exposed")] += 1
            C[("ALL", "free" if free else "exposed")] += 1
print(n, "games: capture-hold turns per game with a spell ready and another group's live camp within 4")
for k in sorted(C): print(k, round(C[k] / n, 2))
