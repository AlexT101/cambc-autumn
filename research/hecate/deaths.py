"""deaths.py BATCH_DIR [team_of_bot (0=bot1,1=bot2,a=all)]: circumstances of champion deaths."""
import json, gzip, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
AN = ROOT / "replays" / ".analysis"
batch = Path(sys.argv[1]).resolve()
which = sys.argv[2] if len(sys.argv) > 2 else "a"
idx = json.loads((AN / "index.json").read_text(encoding="utf-8"))
seen = set(); rows = []
for g in idx["games"]:
    src = Path(g["source"]); src = src if src.is_absolute() else ROOT / src
    if src.resolve().parent == batch and (g["dir"], src.stem[-2:]) not in seen:
        seen.add((g["dir"], src.stem[-2:])); rows.append((g, src.stem))
C = collections.Counter(); N = 0
for g, stem in rows:
    d = AN / g["dir"]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    b1 = 0 if stem.endswith("-12") else 1
    teams = [b1] if which == "0" else [1 - b1] if which == "1" else [0, 1]
    if which == "a" and stem.endswith("-21"): continue
    mp = json.loads((d / meta["mapFile"]).read_text(encoding="utf-8"))
    R = json.load(gzip.open(d / "rounds.json.gz"))
    ri = {r: i for i, r in enumerate(R["round"])}
    champ = {c["id"]: c for c in R["champions"]}
    name = {c["id"]: c["name"] for c in meta["champions"]}
    team = {c["id"]: c["team"] for c in meta["champions"]}
    sp = mp["spawn"]
    centre = [((s["minX"] + s["maxX"]) / 2, (s["minY"] + s["maxY"]) / 2) for s in sp]
    ev = [json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")]
    hits = collections.defaultdict(list)  # victim -> [(r, attacker)]
    camp_hits = collections.defaultdict(list)
    for e in ev:
        if e["k"] in ("attack", "cast"):
            for v, amt in e.get("dmg", []) or []:
                hits[v].append((e["r"], e["a"]))
        if e["k"] == "camp_attack" and e.get("tgt") is not None:
            camp_hits[e["tgt"]].append(e["r"])
        if e["k"] == "death" and not e.get("linked") and team[e["v"]] in teams:
            v = e["v"]; r = e["r"]; N += 1
            atk = {a for (rr, a) in hits[v] if r - 5 <= rr <= r}
            camp = any(r - 5 <= rr <= r for rr in camp_hits[v])
            i0 = ri.get(r - 8, 0)
            c = champ[v]
            hp0 = c["hp"][i0] / c["maxHp"][i0]
            x, y = c["x"][i0], c["y"][i0]
            if x is None: continue
            t = team[v]
            dm = max(abs(x - centre[t][0]), abs(y - centre[t][1])); de = max(abs(x - centre[1 - t][0]), abs(y - centre[1 - t][1]))
            where = "own" if dm < 0.8 * de else ("enemy" if de < 0.8 * dm else "mid")
            C[f"attackers={min(len(atk),3)}"] += 1
            C[f"camp_involved={camp}"] += 1
            C[f"hp8_before={'<50%' if hp0 < 0.5 else '50-90%' if hp0 < 0.9 else '>90%'}"] += 1
            C[f"where={where}"] += 1
            C[f"by={'camp' if e.get('by') == 'camp' else 'champ'}"] += 1
            C[f"victim={name[v]}"] += 1
            C[f"bag={'0' if not e.get('gems') else '1-39' if e['gems'] < 40 else '40+'}"] += 1
            C[f"round={'<=100' if r <= 100 else '101-300' if r <= 300 else '>300'}"] += 1
print(f"{N} deaths in {len(rows)} games")
for k in sorted(C): print(f"  {k:24s} {C[k]:5d} {100*C[k]/N:5.1f}%")
