"""Flatten collect.py rows to a numpy table.  python3 flat.py OUT.npz IN.jsonl.gz [...]"""
import gzip, json, sys
import numpy as np

F = ["tag", "game", "team", "r", "me", "hp", "mhp", "m", "verdict", "falls", "dec", "na", "ne", "nunseen", "nwalk", "gap", "md3", "md10", "md20",
     "od10", "od20", "td10", "td20", "first", "mine3", "taken3", "ours5", "theirs5", "home0", "drop3", "gems", "won", "ranged", "t1", "o1", "t5", "o5",
     "tgt_dies", "flags", "tku", "tkt", "sf", "lost", "ally_busy", "ally_near_idle", "type", "tgt_hp", "tgt_mhp_share", "boost"]
DEC = {c: i for i, c in enumerate("?RFCBkGhUPEWXTKtSHQGrA-")}
FIRST = {"none": 0, "ours": 1, "theirs": 2}
TYPES = {}
games = {}
out = {f: [] for f in F}
for path in sys.argv[2:]:
    for line in gzip.open(path, "rt"):
        d = json.loads(line)
        g = games.setdefault(path + d["game"], len(games))
        vis = [e for e in d["enemies"] if e["vis"]]
        allies = [a for a in d["allies"] if a["id"] != d["me"]]
        tgt = next((e for e in d["enemies"] if e["id"] == d["target"]), None)
        row = dict(tag=0 if d["tag"] == "CS" else 1, game=g, team=d["team"], r=d["r"], me=d["me"], hp=d["hp"], mhp=d["mhp"], m=d["m"],
                   verdict=d["verdict"], falls=d["falls"], dec=DEC.get(d["dec"], 0), na=len(d["allies"]), ne=len(d["enemies"]),
                   nunseen=sum(1 for e in d["enemies"] if not e["vis"]), nwalk=sum(1 for e in d["enemies"] if e["arr"] > 0),
                   gap=min((e["d"] for e in vis), default=-1), md3=d["me_dies3"], md10=d["me_dies10"], md20=d["me_dies20"],
                   od10=d["ours_dead10"], od20=d["ours_dead20"], td10=d["theirs_dead10"], td20=d["theirs_dead20"], first=FIRST[d["first"]],
                   mine3=d["mine3"], taken3=d["taken3"], ours5=d["ours5"], theirs5=d["theirs5"], home0=-1 if d["home0"] is None else d["home0"],
                   drop3=-99 if d["home_drop3"] is None else d["home_drop3"], gems=d["gems"], won=d["won_game"], ranged=int(d["ranged"]),
                   t1=d.get("sim_t1", -1), o1=d.get("sim_o1", -1), t5=d.get("sim_t5", -1), o5=d.get("sim_o5", -1),
                   tgt_dies=d.get("target_dies10", -1), flags=d["flags"], tku=d["tku"], tkt=d["tkt"], sf=d["sf"], lost=d["lost"],
                   ally_busy=sum(1 for a in allies if a.get("dec", "?") in "RKBTtPWh" or a.get("chan", 0)),
                   ally_near_idle=sum(1 for a in allies if a["arr"] == 0 and a["hit"] > 1),
                   type=TYPES.setdefault(d["type"], len(TYPES)), tgt_hp=tgt["hp"] if tgt else -1,
                   tgt_mhp_share=-1, boost=d["boost"])
        for f in F:
            out[f].append(row[f])
np.savez_compressed(sys.argv[1], **{f: np.array(v, dtype=np.float32 if f in ("m", "boost") else np.int32) for f, v in out.items()},
                    types=np.array(list(TYPES)), decs=np.array(list(DEC)))
print(len(out["tag"]), "rows", len(games), "games")
