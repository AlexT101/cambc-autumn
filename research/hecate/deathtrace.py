"""deathtrace.py ANALYSIS_DIR [n]: for the first n champion-kill deaths, print the last 10 rounds of victim and its attackers."""
import json, gzip, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
AN = ROOT / "replays" / ".analysis"
d = AN / sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
R = json.load(gzip.open(d / "rounds.json.gz")); ri = {r: i for i, r in enumerate(R["round"])}
ch = {c["id"]: c for c in R["champions"]}
name = {c["id"]: f'{c["name"]}{c["id"]}T{c["team"]}' for c in meta["champions"]}
ev = [json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")]
acts = collections.defaultdict(list)
for e in ev:
    if "a" in e: acts[(e["r"], e["a"])].append(e)
print(meta["map"]["name"], meta["result"])
shown = 0
for e in ev:
    if e["k"] != "death" or e.get("linked") or e.get("by") == "camp": continue
    v, r = e["v"], e["r"]
    involved = {v} | {x["a"] for x in ev if x["k"] in ("attack", "cast") and r - 10 <= x["r"] <= r and any(t == v for t, _ in (x.get("dmg") or []))}
    print(f"--- {name[v]} dies r{r} by {name.get(e.get('by'), e.get('by'))} bag {e.get('gems')}")
    for rr in range(r - 10, r + 1):
        i = ri.get(rr)
        if i is None: continue
        line = []
        for c in sorted(involved):
            C = ch[c]
            a = ",".join(f'{x["k"][:3]}{"->"+name.get(x.get("tgt"),"").split("T")[0] if x.get("tgt") else ""}{"@camp" if "camp" in x else ""}' for x in acts.get((rr, c), []) if x["k"] not in ("ward",))
            line.append(f'{name[c]}({C["x"][i]},{C["y"][i]} hp{int(C["hp"][i]) if C["hp"][i] is not None else "-"} s{C["sees"][i] if "sees" in C else ""}) {a}')
        print(f"  r{rr}: " + " | ".join(line))
    shown += 1
    if shown >= n: break
