"""Join fishcal trace lines (CS / CC verdicts, HG turn-end reach) with what happened next in the game.

    python3 collect.py live VERSION OUT.jsonl.gz      # direct_batch.py re-runs of replays/<VERSION>, outcomes from the ladder replays
    python3 collect.py self BATCH_DIR OUT.jsonl.gz    # a local debug batch whose bots both log (self-play)

Outcomes come from extract.mjs tables keyed by the replay's sha256: replays/fishcal/analysis, or a version's
extract/ladder (pipeline.py's extract step). A live game's rows are kept only through its `ladder_trusted_through`
round (tools/replay/harness/direct_batch.py's direct_validation.json): until then the traced bot's state is the
ladder bot's, so its verdicts are the ones that played. The outcome window may run past it, since it reads the ladder game.

Verdict rows follow cal-tools/collect.py (the last stand of a turn, one chase row per target). HG rows: one per enemy
the turn-end line lists, with the damage that enemy then dealt us before our next turn (`real`), against the strike
model's `at` and `blow`."""
import gzip, hashlib, json, sys, zipfile
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AN = ROOT / "replays" / "fishcal" / "analysis"
CACHES = [AN, *sorted((ROOT / "replays").glob("v*/extract/ladder"))]
RANGED = {"Vesper Vale", "Cassi", "Stellar", "Prism", "Willow", "Tavi"}


def parse(text):
    cal, dec, hg = [], {}, []
    for line in text.splitlines():
        line = line.replace("\x00", "")
        if line.startswith("D "):
            p = line.split()
            try:
                dec[(int(p[1]), int(p[2]))] = p[3]
            except (ValueError, IndexError):
                pass
            continue
        if line.startswith("HG "):
            try:
                head, en = line.split("|")
                p = head.split()
                hg.append(dict(r=int(p[1]), me=int(p[2]), x=int(p[3]), y=int(p[4]), hp=int(p[5]), dec=p[6], priced=int(p[7]),
                               enemies=[dict(zip(("id", "d", "at", "blow", "stun"), map(int, s.split(":")))) for s in en.split()]))
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
            d["sim_t1"], d["sim_o1"], d["sim_t5"], d["sim_o5"] = map(int, p[19:23])
            d["allies"] = [dict(zip(("id", "arr", "hp"), map(int, s.split(":")))) for s in al.split()]
            d["enemies"] = [dict(zip(("id", "vis", "arr", "d", "hp"), map(int, s.split(":")))) for s in en.split()]
        except (ValueError, IndexError):
            continue
        d["verdict"] = int(bool(d["lost"] or (d["falls"] and d["sf"])))
        cal.append(d)
    return cal, dec, hg


def game_rows(job):
    """job: replay path, {team: stdout text path or (zip, member)}, {team: last trusted round}, extra fields."""
    replay, stdouts, trusted, extra = job
    raw = Path(replay).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:16]
    folder = next((c / sha for c in CACHES if (c / sha / "meta.json").is_file()), None)
    if folder is None:
        return [], [], f"no extract for {replay}"
    meta = json.loads((folder / "meta.json").read_text())
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
    died = defaultdict(list)
    dmg = []  # (s, r, att, vic, amount)
    first_step, last_step = {}, {}
    for e in events:
        if e["k"] == "death":
            died[e["v"]].append((e["r"], e["s"]))
        if "a" in e and e.get("t", -1) >= 0:
            first_step.setdefault((e["a"], e["r"]), e["s"])
            last_step[(e["a"], e["r"])] = e["s"]
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
    rows, hrows = [], []
    for team, src in stdouts.items():
        if isinstance(src, tuple):
            with zipfile.ZipFile(src[0]) as z:
                text = z.read(src[1]).decode("utf-8", "replace")
        else:
            text = gzip.open(src, "rt", encoding="utf-8", errors="replace").read()
        cal, dec, hg = parse(text)
        last_ok = trusted.get(team, 10**9)
        base = dict(extra, team=team, won_game=int(winner == team), map=meta["map"]["name"])
        # Verdicts.
        last = {}
        for d in cal:
            if d["tag"] == "CS":
                last[(d["r"], d["me"])] = d
        seen_cc, out = set(), list(last.values())
        for d in cal:
            if d["tag"] == "CC" and (k := (d["r"], d["me"], d["target"])) not in seen_cc:
                seen_cc.add(k)
                out.append(d)
        for d in out:
            r, me = d["r"], d["me"]
            if r > last_ok or me not in champs or champs[me]["team"] != team:
                continue
            d.update(base)
            d["type"] = champs[me]["name"]
            d["ranged"] = d["type"] in RANGED
            d["dec"] = dec.get((r, me), "?")
            ours = {a["id"] for a in d["allies"]} | {me}
            ours |= {linked[i] for i in list(ours) if i in linked}
            foes = {e["id"] for e in d["enemies"]}
            foes |= {linked[i] for i in list(foes) if i in linked}
            s0 = first_step.get((me, r), 0)

            def death(i, k=10):
                for rr, ss in died.get(i, []):
                    if r <= rr <= r + k and ss >= s0:
                        return rr
                return None
            for k in (3, 5, 10, 20):
                d[f"me_dies{k}"] = int(death(me, k) is not None or (me in linked and death(linked[me], k) is not None))
                d[f"ours_dead{k}"] = len({pick[i] for i in ours if death(i, k) is not None})
                d[f"theirs_dead{k}"] = len({pick[i] for i in foes if death(i, k) is not None})
            if d["tag"] == "CC":
                t = d["target"]
                d["target_dies10"] = int(death(t) is not None or (t in linked and death(linked[t]) is not None))
            fo = min((x for i in ours if (x := death(i)) is not None), default=None)
            ft = min((x for i in foes if (x := death(i)) is not None), default=None)
            d["first"] = "none" if fo is None and ft is None else "ours" if ft is None or (fo is not None and fo <= ft) else "theirs"
            mine3 = taken3 = ours5 = theirs5 = 0.0
            enemy_hit, ally_hit = defaultdict(lambda: 99), defaultdict(lambda: 99)
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
                e["hit"] = min(enemy_hit[e["id"]], enemy_hit[linked[e["id"]]] if e["id"] in linked else 99)
                e["type"] = champs.get(e["id"], {}).get("name", "?")
            for a in d["allies"]:
                a["hit"] = ally_hit[a["id"]]
                a["dec"] = dec.get((r, a["id"]), dec.get((r + 1, a["id"]), "?"))
                a["type"] = champs.get(a["id"], {}).get("name", "?")
            i0 = rix.get(r - 1)
            d["gems"] = cr[me]["gems"][i0] if i0 is not None and me in cr else 0
            rows.append(d)
        # Turn-end reach: damage each listed enemy dealt us after our turn, before our next one.
        for h in hg:
            r, me = h["r"], h["me"]
            if r > last_ok or me not in champs or champs[me]["team"] != team:
                continue
            s_end = last_step.get((me, r))
            if s_end is None:
                continue
            s_next = first_step.get((me, r + 1), 1 << 60)
            got = defaultdict(float)
            for rr in (r, r + 1):
                for (s, _, att, vic, amount) in dmg_by_round.get(rr, ()):
                    if vic == me and s_end < s < s_next:
                        got[att] += amount
            ix = rix.get(r)  # the snapshot after round r: we do not move after our turn
            for e in h["enemies"]:
                hrows.append(dict(base, r=r, me=me, type=champs[me]["name"], dec=h["dec"], hp=h["hp"], e=e["id"],
                                  etype=champs.get(e["id"], {}).get("name", "?"), d=e["d"], at=e["at"], blow=e["blow"], stun=e["stun"],
                                  real=round(got.get(e["id"], 0.0), 1), n_reach=len(h["enemies"]), priced=h["priced"],
                                  pos_ok=int(ix is not None and cr[me]["x"][ix] == h["x"] and cr[me]["y"][ix] == h["y"])))
    return rows, hrows, None


def live_jobs(version):
    vdir = ROOT / "replays" / version
    man = json.loads((vdir / "manifest.json").read_text())["games"]
    tv = json.loads((vdir / "runs/direct/direct_validation.json").read_text())
    jobs = []
    for g in man:
        key = f"{g['group'][:8]}-{g['position']}"
        t = tv.get(key)
        trace = vdir / "runs/direct" / key / "trace.stdout.gz"
        if not t or t.get("status") != "ok" or not trace.exists() or t.get("ladder_trusted_through") is None:
            continue
        team = 0 if g["our_side"] == "a" else 1
        rsha = hashlib.sha256((ROOT / g["replay"]).read_bytes()).hexdigest()[:16]
        jobs.append((str(ROOT / g["replay"]), {team: str(trace)}, {team: t["ladder_trusted_through"]},
                     dict(src="live", version=version, game=key, rsha=rsha, opp=g["opponent"], refset=g.get("refset"), rounds=g["rounds"],
                          trusted=t["ladder_trusted_through"])))
    return jobs


def self_jobs(batch):
    jobs, seen = [], set()
    for p in sorted(Path(batch).rglob("*.repl26a")):
        # Both seats run the same code, so a map's two side assignments can be the same game byte for byte.
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        jobs.append((str(p), {0: (str(p), "team-a.stdout"), 1: (str(p), "team-b.stdout")}, {},
                     dict(src="self", version=Path(batch).name, game=str(p.relative_to(batch)), opp="self", refset=None)))
    return jobs


def main():
    mode, arg, out = sys.argv[1:4]
    jobs = live_jobs(arg) if mode == "live" else self_jobs(arg)
    n = nh = bad = 0
    with Pool(int(__import__("os").environ.get("NP", "16"))) as pool, gzip.open(out, "wt") as f, \
            gzip.open(out.replace(".jsonl.gz", ".hg.jsonl.gz"), "wt") as fh:
        for rows, hrows, err in pool.imap_unordered(game_rows, jobs, chunksize=2):
            if err:
                bad += 1
                print(err, file=sys.stderr)
            for d in rows:
                f.write(json.dumps(d) + "\n")
            for d in hrows:
                fh.write(json.dumps(d) + "\n")
            n, nh = n + len(rows), nh + len(hrows)
    print(f"{n} verdict rows, {nh} HG rows from {len(jobs)} games ({bad} without extract)")


if __name__ == "__main__":
    main()
