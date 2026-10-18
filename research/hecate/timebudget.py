"""timebudget.py BATCH_DIR [team_bot_index]: share of champion-rounds by activity for bot 1 (or 2)."""
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
T = collections.Counter(); rounds_total = 0
for g, stem in rows:
    d = AN / g["dir"]
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    team = (0 if stem.endswith("-12") else 1) ^ which
    R = json.load(gzip.open(d / "rounds.json.gz"))
    ev = [json.loads(l) for l in gzip.open(d / "events.jsonl.gz", "rt")]
    ids = [c["id"] for c in meta["champions"] if c["team"] == team]
    act = collections.defaultdict(set)  # (r, id) -> kinds
    for e in ev:
        if e.get("a") in ids:
            k = e["k"]
            if k == "attack": k = "attack_camp" if "camp" in e else ("attack_lock" if e.get("lock") else "attack_champ")
            if k == "cast": k = "cast_camp" if "camp" in e or e.get("cdmg") else ("cast_champ" if e.get("dmg") else "cast_other")
            act[(e["r"], e["a"])].add(k)
    chs = [c for c in R["champions"] if c["id"] in ids]
    for c in chs:
        for i, r in enumerate(R["round"]):
            ks = act.get((r, c["id"]), set())
            if not c["alive"][i]: cat = "dead"
            elif c["chan"][i] == 2: cat = "tribute"
            elif c["chan"][i] == 1 and c["chanT"][i] <= 3: cat = "recall_kept"
            elif ks & {"attack_camp", "cast_camp"}: cat = "camp_hit" + ("+move" if "move" in ks else "")
            elif ks & {"attack_champ", "cast_champ"}: cat = "fight"
            elif "move" in ks or "cast_other" in ks:
                cat = "move_bag" if c["gems"][i] > 0 else "move_empty"
            else: cat = "still"
            if cat.startswith("move") and i > 0 and c["hp"][i] < 0.999 * c["maxHp"][i] and c["gems"][i] == 0: cat += "_hurt"
            T[cat] += 1
        rounds_total += len(R["round"])
tot = sum(T.values())
print(f"{len(rows)} games, mean {rounds_total/len(rows)/len(chs):.0f} rounds")
for k, v in T.most_common(): print(f"  {k:14s} {100*v/tot:5.1f}%")
