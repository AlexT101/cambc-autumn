"""timeline.py REPLAY_STEM_OR_DIR [champ_type] [max_round]: compact per-champion activity segments.
Pass an analysis dir name (replays/.analysis/<dir>) or a replay path."""
import json, gzip, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
AN = ROOT / "replays" / ".analysis"
arg = sys.argv[1]
want = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None
maxr = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
d = AN / arg
if not d.exists():
    idx = json.loads((AN / "index.json").read_text(encoding="utf-8"))
    p = Path(arg).resolve()
    d = AN / next(g["dir"] for g in idx["games"] if (Path(g["source"]) if Path(g["source"]).is_absolute() else ROOT / g["source"]).resolve() == p)
meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
mp = json.loads((d / meta["mapFile"]).read_text(encoding="utf-8")) if "mapFile" in meta else None
R = json.load(gzip.open(d / "rounds.json.gz"))
ev = [json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")]
camp_group = {c["id"]: c["group"] for c in mp["camps"]} if mp else {}
print(meta["map"]["name"], meta["map"]["width"], "x", meta["map"]["height"], "teams", [t.get("name") for t in meta["teams"]], "result", meta["result"])
act = collections.defaultdict(list)
for e in ev:
    if "a" in e: act[(e["r"], e["a"])].append(e)
    if e["k"] == "death": act[(e["r"], e["v"])].append(e)
names = {c["id"]: f'{c["name"]}#{c["id"]}(T{c["team"]})' for c in meta["champions"]}
for ci, c in enumerate(R["champions"]):
    if want and want.lower() not in names[c["id"]].lower(): continue
    print("==", names[c["id"]])
    seg = None
    def flush():
        if seg: print(f'  r{seg[0]:4d}-{seg[1]:4d} {seg[2]:18s} {seg[3]} -> {seg[4]} hp {seg[5]}->{seg[6]} gems {seg[7]}->{seg[8]}')
    for i, r in enumerate(R["round"]):
        if r > maxr: break
        es = act.get((r, c["id"]), [])
        ks = [e["k"] for e in es]
        label = "still"
        if not c["alive"][i]: label = "dead"
        elif c["chan"][i] == 2: label = "tribute"
        elif c["chan"][i] == 1 and c["chanT"][i] <= 3: label = "recall"
        for e in es:
            if e["k"] in ("attack", "cast") and "camp" in e: label = f'camp g{camp_group.get(e["camp"], "?")}'
            elif e["k"] in ("attack", "cast") and "tgt" in e: label = f'FIGHT {names.get(e["tgt"], e["tgt"]).split("(")[0]}'
            elif e["k"] == "death": label = f'DIED by {e.get("by")}'
        if label == "still" and "move" in ks: label = "walk"
        pos = (c["x"][i], c["y"][i]); hp = int(c["hp"][i]); gm = c["gems"][i]
        if seg and seg[2] == label: seg[1] = r; seg[4] = pos; seg[6] = hp; seg[8] = gm
        else:
            flush(); seg = [r, r, label, pos, pos, hp, hp, gm, gm]
    flush()
