"""Join cal-dbg's CS / CC verdict lines with what happened next. Writes one JSON row per verdict.

    python3 collect.py OUT.jsonl.gz BATCH_DIR [BATCH_DIR...]

Lines (both teams' stdout when both bots log): CS stand verdicts (stand_lost_at), CC chase verdicts (prey), D decisions.
"""
import gzip, hashlib, json, sys, zipfile
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

ROOT = Path("/home/ubuntu/cambc-autumn")
AN = ROOT / "replays" / ".analysis"
K = 10
RANGED = {"Vesper Vale", "Cassi", "Stellar", "Prism", "Willow", "Tavi"}


def parse(text):
    cal, dec = [], {}
    for line in text.splitlines():
        line = line.replace("\x00", "")
        if line.startswith("D "):
            p = line.split()
            try:
                dec[(int(p[1]), int(p[2]))] = p[3]
            except (ValueError, IndexError):
                pass
            continue
        if not (line.startswith("CS ") or line.startswith("CC ")):
            continue
        try:
            head, al, en = line.split("|")
            p = head.split()
            d = dict(tag=p[0], r=int(p[1]), me=int(p[2]), x=int(p[3]), y=int(p[4]), hp=int(p[5]), mhp=int(p[6]), target=int(p[7]),
                     flags=int(p[8]), falls=int(p[9]), lost=int(p[10]), sf=int(p[11]), tku=int(p[12]), tkt=int(p[13]), m=int(p[14]) / 100,
                     v1=int(p[15]), camp=int(p[16]), boost=int(p[17]) / 100, tf=int(p[18]))
            if len(p) >= 23:
                d["sim_t1"], d["sim_o1"], d["sim_t5"], d["sim_o5"] = map(int, p[19:23])
            d["allies"] = [dict(zip(("id", "arr", "hp"), map(int, s.split(":")))) for s in al.split()]
            d["enemies"] = [dict(zip(("id", "vis", "arr", "d", "hp"), map(int, s.split(":")))) for s in en.split()]
        except (ValueError, IndexError):
            continue
        d["verdict"] = int(bool(d["lost"] or (d["falls"] and d["sf"])))
        cal.append(d)
    return cal, dec


def one(path):
    path = Path(path)
    raw = path.read_bytes()
    folder = AN / hashlib.sha256(raw).hexdigest()[:16]
    if not (folder / "meta.json").is_file():
        return []
    meta = json.loads((folder / "meta.json").read_text())
    z = zipfile.ZipFile(path)
    names = z.namelist()
    champs = {c["id"]: c for c in meta["champions"]}
    linked = {}
    for c in meta["champions"]:
        for o in meta["champions"]:
            if c["team"] == o["team"] and c["id"] != o["id"] and {c["name"], o["name"]} == {"Cassi", "Issac"}:
                linked[c["id"]] = o["id"]
    pick = {i: min(i, linked.get(i, i)) for i in champs}
    events = [json.loads(l) for l in gzip.open(folder / "events.jsonl.gz", "rt") if l.strip()]
    rounds = json.load(gzip.open(folder / "rounds.json.gz"))
    rix = {r: i for i, r in enumerate(rounds["round"])}
    cr = {c["id"]: c for c in rounds["champions"]}
    mp = json.loads((AN / meta["mapFile"]).read_text()) if (AN / meta["mapFile"]).is_file() else json.loads((folder / meta["mapFile"]).resolve().read_text())
    spawn = mp["spawn"]
    died = defaultdict(list)
    dmg = []  # (s, r, att, vic, amount)
    first_step = {}
    for e in events:
        if e["k"] == "death":
            died[e["v"]].append((e["r"], e["s"], e.get("by", -1) if "by" in e else -2))
        if "a" in e and e.get("t", -1) >= 0:
            first_step.setdefault((e["a"], e["r"]), e["s"])
        if e["k"] in ("attack", "cast"):
            for vic, amount in e.get("dmg") or []:
                if vic in champs:
                    dmg.append((e["s"], e["r"], e["a"], vic, amount))
            if e.get("refl"):
                dmg.append((e["s"], e["r"], e["reflBy"], e["a"], e["refl"]))
    dmg.sort()
    dmg_by_round = defaultdict(list)
    for x in dmg:
        dmg_by_round[x[1]].append(x)
    winner = meta["result"]["winner"]
    rows = []
    for team, name in ((0, "team-a.stdout"), (1, "team-b.stdout")):
        if name not in names:
            continue
        cal, dec = parse(z.read(name).decode("utf-8", "replace"))
        if not cal:
            continue
        sp = spawn[team]
        last = {}
        for d in cal:
            if d["tag"] == "CS":
                last[(d["r"], d["me"])] = d  # the decision reads the last stand of the turn
        seen_cc = set()
        out = list(last.values())
        for d in cal:
            if d["tag"] == "CC":
                k = (d["r"], d["me"], d["target"])
                if k in seen_cc:
                    continue
                seen_cc.add(k)
                out.append(d)
        for d in out:
            r, me = d["r"], d["me"]
            if me not in champs or champs[me]["team"] != team:
                continue
            d["game"] = path.name
            d["map"] = meta["map"]["name"]
            d["team"] = team
            d["won_game"] = int(winner == team)
            d["type"] = champs[me]["name"]
            d["ranged"] = d["type"] in RANGED
            d["dec"] = dec.get((r, me), "?")
            ours = {a["id"] for a in d["allies"]} | {me}
            ours |= {linked[i] for i in list(ours) if i in linked}
            foes = {e["id"] for e in d["enemies"]}
            foes |= {linked[i] for i in list(foes) if i in linked}
            s0 = first_step.get((me, r), 0)

            def death(i, k=K):
                for (rr, ss, by) in died.get(i, []):
                    if r <= rr <= r + k and ss >= s0:
                        return rr
                return None
            for k in (3, 5, 10, 20):
                our_dead = {pick[i] for i in ours if death(i, k) is not None}
                their_dead = {pick[i] for i in foes if death(i, k) is not None}
                d[f"me_dies{k}"] = int(death(me, k) is not None or (me in linked and death(linked[me], k) is not None))
                d[f"ours_dead{k}"] = len(our_dead)
                d[f"theirs_dead{k}"] = len(their_dead)
            if d["tag"] == "CC":
                t = d["target"]
                d["target_dies10"] = int(death(t) is not None or (t in linked and death(linked[t]) is not None))
            fo = min((death(i) for i in ours if death(i) is not None), default=None)
            ft = min((death(i) for i in foes if death(i) is not None), default=None)
            d["first"] = "none" if fo is None and ft is None else "ours" if ft is None or (fo is not None and fo <= ft) else "theirs"
            # damage exchanges
            dealt = defaultdict(float)  # by our champion to the roster enemies, per window
            mine3 = taken3 = 0.0
            ours5 = theirs5 = 0.0
            on_weak = 0.0
            enemy_hit = defaultdict(lambda: 99)  # first round (offset) each roster enemy hits our roster
            ally_hit = defaultdict(lambda: 99)
            for rr in range(r, r + 6):
                for (s, _, att, vic, amount) in dmg_by_round.get(rr, ()):
                    if s < s0:
                        continue
                    if att in ours and vic in foes:
                        ours5 += amount
                        if rr <= r + 3 and att == me:
                            mine3 += amount
                        ally_hit[att] = min(ally_hit[att], rr - r)
                    elif att in foes and vic in ours:
                        theirs5 += amount
                        if rr <= r + 3 and vic == me:
                            taken3 += amount
                        enemy_hit[att] = min(enemy_hit[att], rr - r)
            d["mine3"], d["taken3"], d["ours5"], d["theirs5"] = round(mine3), round(taken3), round(ours5), round(theirs5)
            for e in d["enemies"]:
                e["hit"] = min(enemy_hit[e["id"]], enemy_hit[linked.get(e["id"], -1)] if e["id"] in linked else 99)
                e["type"] = champs.get(e["id"], {}).get("name", "?")
            for a in d["allies"]:
                a["hit"] = ally_hit[a["id"]]
                a["dec"] = dec.get((r, a["id"]), dec.get((r + 1, a["id"]), "?"))
                i0a = rix.get(r - 1)
                a["chan"] = cr[a["id"]]["chan"][i0a] if i0a is not None and a["id"] in cr else 0
                a["type"] = champs.get(a["id"], {}).get("name", "?")
            # home distance now and 3 rounds later (Chebyshev to own spawn box)
            def home(rr):
                i = rix.get(rr)
                c = cr[me]
                if i is None or not c["alive"][i]:
                    return None
                x, y = c["x"][i], c["y"][i]
                return max(max(sp["minX"] - x, 0, x - sp["maxX"]), max(sp["minY"] - y, 0, y - sp["maxY"]))
            h0, h3 = home(r - 1), home(r + 2)
            d["home0"] = h0
            d["home_drop3"] = None if h0 is None or h3 is None else h0 - h3
            # carried gems at the start
            i0 = rix.get(r - 1)
            d["gems"] = cr[me]["gems"][i0] if i0 is not None else 0
            rows.append(d)
    return rows


def main():
    out = sys.argv[1]
    files = []
    for a in sys.argv[2:]:
        files += sorted(str(p) for p in Path(a).glob("*.repl26a"))
    n = 0
    with Pool(int(__import__("os").environ.get("NP", "16"))) as pool, gzip.open(out, "wt") as f:
        for rows in pool.imap_unordered(one, files, chunksize=4):
            for d in rows:
                f.write(json.dumps(d) + "\n")
                n += 1
    print(n, "rows from", len(files), "games")


if __name__ == "__main__":
    main()
