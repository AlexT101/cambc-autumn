"""Fight-model calibration: morgana's fight predictions against what happened.

Build a copy of morgana with `debug_fights = true` (src/util.h), play batches with replays as
bot 1, extract them, then:

    py run_batched.py variants/morgana-cal baselines/morgana-v5 --gen
    node tools/replay/extract.mjs replays/batch-X
    py tools/replay/fight_calibration.py replays/batch-X [more batches...] [--by FIELD,...]

Each champion prints "FF" for every turn that starts in reach of a credible enemy (Safety::fight
at its tile) and "FC" for every chase (Safety::fight at the prey's tile): round, id, tile, health,
the turn's branch letter (see `decision` in bot.cpp), lost, turns to kill us / them, allies,
enemies, pooled health of each side, target, camp damage, lethal, the simulation's damage by
each side in its first turn and its first five (theirs first: Trade::dealt), then the allies in the fight (`a<id>`) and the enemies in
reach (`<id><v|u>:<distance>:<strike at that distance>:<rounds since seen>`).

Outcomes: deaths within K rounds; damage the enemies in the fight deal our side before our next
turn (against the simulation's first enemy turn, which is their best strike) and over W rounds
(against W of the simulation's turns), and ours to them. Sides come from the file names (bot 1
logs: `-12` files are team A), so a game's cached meta.json team names are never needed.
"""
import argparse
import bisect
import gzip
import hashlib
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

AN = Path(__file__).resolve().parents[2] / "replays" / ".analysis"
K = 10
W = 5
RANGED = {"Vesper Vale", "Cassi", "Stellar", "Prism", "Willow", "Tavi"}


def parse(text):
    out = []
    for line in text.splitlines():
        p = line.replace("\x00", "").split()
        if not p or p[0] not in ("FF", "FC"):
            continue
        try:
            d = dict(tag=p[0], r=int(p[1]), me=int(p[2]), x=int(p[3]), y=int(p[4]), hp=int(p[5]), dec=p[6],
                     lost=int(p[7]), tku=int(p[8]), tkt=int(p[9]), allies=int(p[10]), enemies=int(p[11]),
                     ourpool=int(p[12]), theirpool=int(p[13]), target=int(p[14]), camp=int(p[15]), lethal=int(p[16]),
                     their_first=float(p[17]), our_first=float(p[18]), their_five=float(p[19]), our_five=float(p[20]),
                     mates=[], foes=[])
            for s in p[21:]:
                if s[0] == "a":
                    d["mates"].append(int(s[1:]))
                else:
                    f = s.split(":")
                    d["foes"].append(dict(id=int(f[0][:-1]), vis=f[0][-1] == "v", d=int(f[1]), strike=int(f[2]), age=int(f[3])))
        except (ValueError, IndexError):
            continue
        out.append(d)
    return out


def games(dirs):
    for a in dirs:
        for path in sorted(Path(a).glob("*.repl26a")):
            folder = AN / hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            if not (folder / "meta.json").is_file():
                print(f"skip {path}: not extracted", file=sys.stderr)
                continue
            side = 0 if path.stem.endswith("-12") else 1
            z = zipfile.ZipFile(path)
            name = "team-a.stdout" if side == 0 else "team-b.stdout"
            text = z.read(name).decode("utf-8", "replace") if name in z.namelist() else ""
            meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
            events = [json.loads(line) for line in gzip.open(folder / "events.jsonl.gz", "rt", encoding="utf-8") if line.strip()]
            yield path, side, parse(text), meta, events


def hp_bin(hp):
    return "<200" if hp < 200 else "200-400" if hp < 400 else "400-700" if hp < 700 else "700+"


def outcomes(d, idx, turn_step, died_at, linked):
    """What happened after a logged line."""
    me, r = d["me"], d["r"]
    ours = {me, *d["mates"]}
    ours |= {linked[i] for i in list(ours) if i in linked}
    foes = {f["id"] for f in d["foes"]}
    foes |= {linked[i] for i in list(foes) if i in linked}
    s0 = turn_step.get((me, r), idx["round_start"].get(r + 1, 0) - 1)
    s1 = turn_step.get((me, r + 1), idx["round_start"].get(r + 2, 1 << 40) - 1)
    sw = idx["round_start"].get(r + W + 1, 1 << 40)
    first = their = mine = 0.0
    by_foe = defaultdict(lambda: [0.0, 0.0])
    dmg = idx["dmg"]
    for e in dmg[bisect.bisect_right(dmg, (s0, 1 << 40)):]:
        if e[0] >= sw:
            break
        _, att, vic, amount = e
        if att in foes and vic in ours:
            their += amount
            by_foe[att][1] += amount
            if e[0] < s1:
                first += amount
                by_foe[att][0] += amount
        elif att in ours and vic in foes:
            mine += amount
    for f in d["foes"]:
        f["real1"], f["real5"] = by_foe[f["id"]][0] + by_foe[linked.get(f["id"], -1)][0], by_foe[f["id"]][1]
    d["real_first"], d["real_their"], d["real_ours"] = first, their, mine
    d["engaged"] = their > 0 and mine > 0

    def death(i):
        return min((x for x in died_at.get(i, []) if r <= x <= r + K), default=None)

    d["we_die"] = death(me) is not None
    d["foe_dies"] = any(death(i) is not None for i in foes)
    ours_first = min((x for i in ours if (x := death(i)) is not None), default=1 << 20)
    theirs_first = min((x for i in foes if (x := death(i)) is not None), default=1 << 20)
    d["first_death"] = "none" if ours_first == theirs_first == 1 << 20 else "ours" if ours_first <= theirs_first else "theirs"


def collect(dirs):
    rows = []
    for path, side, lines, meta, events in games(dirs):
        types = {c["id"]: c["name"] for c in meta["champions"]}
        linked = {}
        for c in meta["champions"]:
            for o in meta["champions"]:
                if c["team"] == o["team"] and {c["name"], o["name"]} == {"Cassi", "Issac"}:
                    linked[c["id"]] = o["id"]
        died_at = defaultdict(list)
        turn_step = {}
        idx = {"dmg": [], "round_start": {}}
        for e in events:
            idx["round_start"].setdefault(e["r"], e["s"])
            if e["k"] == "death":
                died_at[e["v"]].append(e["r"])
            if "a" in e and e["t"] >= 0:
                turn_step[(e["a"], e["r"])] = max(turn_step.get((e["a"], e["r"]), 0), e["s"])
            if e["k"] in ("attack", "cast"):
                for vic, amount in e.get("dmg") or []:
                    idx["dmg"].append((e["s"], e["a"], vic, amount))
                if e.get("refl"):
                    idx["dmg"].append((e["s"], e["reflBy"], e["a"], e["refl"]))
        idx["dmg"].sort(key=lambda e: e[0])
        for d in lines:
            d["game"] = path.name
            d["type"] = types.get(d["me"], "?")
            d["ranged"] = d["type"] in RANGED
            for f in d["foes"]:
                f["type"] = types.get(f["id"], "?")
            outcomes(d, idx, turn_step, died_at, linked)
            rows.append(d)
    return rows


def keyed(d, field):
    foes = d["foes"]
    match field:
        case "lost": return "lost" if d["lost"] else "won"
        case "tag": return d["tag"]
        case "dec": return d["dec"]
        case "allies": return min(d["allies"], 4)
        case "enemies": return min(d["enemies"], 4)
        case "odds": return f"{min(d['allies'], 3)}v{min(d['enemies'], 3)}"
        case "hp": return hp_bin(d["hp"])
        case "range": return "ranged" if d["ranged"] else "melee"
        case "type": return d["type"]
        case "unseen": return "some unseen" if any(not f["vis"] for f in foes) else "all visible"
        case "near": return min((f["d"] for f in foes), default=9)
        case "far": return "all within 3" if all(f["d"] <= 3 for f in foes) else "some 4-5"
        case "tku": return min(d["tku"], 6) if d["tku"] else "-"
        case "tkt": return min(d["tkt"], 6) if d["tkt"] else "-"
        case "camp": return "camp" if d["camp"] > 0 else "no camp"
        case "lethal": return "lethal" if d["lethal"] else "-"
    raise SystemExit(f"unknown field {field}")


def pct(a, b):
    return f"{100 * a / b:5.1f}%" if b else "    -"


def ratio(a, b):
    return f"{a / b:5.2f}" if b else "    -"


def table(rows, fields):
    groups = defaultdict(list)
    for d in rows:
        groups[tuple(keyed(d, f) for f in fields)].append(d)
    print(f"\n{'/'.join(fields):26}     n we die foe dies engaged | engaged: ours 1st theirs 1st | real/sim: theirs 1st  theirs {W}  ours {W}  balance")
    for k in sorted(groups, key=str):
        g = groups[k]
        n = len(g)
        if n < 30:
            continue
        e = [d for d in g if d["engaged"]]
        pt5, rt5 = sum(d["their_five"] for d in g), sum(d["real_their"] for d in g)
        po5, ro5 = sum(d["our_five"] for d in g), sum(d["real_ours"] for d in g)
        # Balance: the real damage ratio (theirs over ours) over the simulated one; above 1, the
        # simulation underrates them.
        balance = (rt5 / ro5) / (pt5 / po5) if ro5 and po5 and pt5 else 0
        print(f"{' '.join(map(str, k)):26} {n:6} {pct(sum(d['we_die'] for d in g), n)} {pct(sum(d['foe_dies'] for d in g), n)}"
              f"  {pct(len(e), n)} |       {pct(sum(d['first_death'] == 'ours' for d in e), len(e))}      {pct(sum(d['first_death'] == 'theirs' for d in e), len(e))} |"
              f"           {ratio(sum(d['real_first'] for d in g), sum(d['their_first'] for d in g))}     {ratio(rt5, pt5)}    {ratio(ro5, po5)}    {balance:5.2f}")


def foe_table(rows, fields):
    groups = defaultdict(list)
    for d in rows:
        for f in d["foes"]:
            key = tuple(min(f["d"], 5) if x == "d" else ("visible" if f["vis"] else "unseen") if x == "vis" else
                        min(f["age"], 5) if x == "age" else f[x] for x in fields)
            groups[key].append(f)
    print(f"\nenemy {'/'.join(fields):20}     n  hits before our next turn  real/strike  hits within {W}")
    for k in sorted(groups, key=str):
        g = groups[k]
        if len(g) < 30:
            continue
        print(f"{' '.join(map(str, k)):26} {len(g):6}  {pct(sum(f['real1'] > 0 for f in g), len(g)):>24}  {ratio(sum(f['real1'] for f in g), sum(f['strike'] for f in g)):>11}  {pct(sum(f['real5'] > 0 for f in g), len(g)):>13}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--by", default="lost;lost,dec;lost,odds;lost,hp;lost,range;lost,type;lost,unseen;lost,far;lost,tku;lost,tkt;lost,camp;lost,lethal")
    ap.add_argument("--foes", default="d,vis;type;age")
    ap.add_argument("--tag", default="FF")
    args = ap.parse_args()
    rows = [d for d in collect(args.dirs) if d["tag"] in args.tag.split(",")]
    print(f"{len(rows)} {args.tag} lines. Deaths within {K} rounds (our own, any enemy in the fight). Engaged: both")
    print(f"sides dealt damage within {W} rounds; then whose side lost a champion first. real/sim: damage dealt")
    print(f"by the enemies in the fight to our side before our next turn and within {W} rounds, and ours to them,")
    print(f"against the simulation's first turn and first {W} turns of that side; balance: the real ratio of")
    print("their damage to ours over the simulated one (above 1: it underrates them).")
    decided = [d for d in rows if d["engaged"] and d["first_death"] != "none"]
    right = sum((d["first_death"] == "ours") == bool(d["lost"]) for d in decided)
    print(f"Engaged fights with a death within {K} rounds: {len(decided)}; the prediction named the side that lost a"
          f" champion first in {pct(right, len(decided))}")
    for spec in args.by.split(";"):
        table(rows, spec.split(","))
    for spec in args.foes.split(";"):
        foe_table(rows, spec.split(","))


main()
