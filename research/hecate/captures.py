"""captures.py ANALYSIS_DIR [maxround]: capture log per team (round, group, comp, gems, sharers), plus per-team cumulative gems."""
import json, gzip, sys, collections
from pathlib import Path
AN = Path(__file__).resolve().parents[2] / "replays" / ".analysis"
d = AN / sys.argv[1]; maxr = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
mp = json.loads((d / meta["mapFile"]).read_text(encoding="utf-8"))
G = {g["id"]: g for g in mp["groups"]}
comp = {g["id"]: "".join(sorted(t[0] for t in g["types"])) for g in mp["groups"]}
print(meta["map"]["name"], [t.get("name") for t in meta["teams"]], meta["result"], "spawns", mp["spawn"])
tot = [0, 0]
for e in (json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")):
    if e["r"] > maxr: break
    if e["k"] == "capture":
        g = G[e["g"]]; gems = sum(s[1] for s in e["shares"]); tot[e["team"]] += gems
        print(f'  r{e["r"]:4d} T{e["team"]} g{e["g"]:3d} {comp[e["g"]]:8s} side{g["side"]:2d} gems {gems:3d} by {len(e["shares"])}  tot {tot}')
