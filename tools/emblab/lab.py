"""Emblem lab: learn which emblems (and, with them, which drafts) win, from self-play games whose drafts and
emblem choices are randomised (tools/emblab/README.md).

    py tools/emblab/lab.py init   --lab NAME [--source REF]     # freeze REF's bots/astraeus, the map table, the prior
    py tools/emblab/lab.py run    --lab NAME --games 12000 [--vehicles 6] [--threads 94]   # one batch
    py tools/emblab/lab.py status --lab NAME

Everything lives in replays/emblab/NAME/: config.json, maps.jsonl, prior.json, games.jsonl (one row per game),
decisions.jsonl (one row per logged emblem decision), lab.log and batches/bNNN/."""
import argparse, collections, json, random, re, subprocess, sys, time, zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "draftlab"))
sys.path.insert(0, str(ROOT / "tools"))
import evehicle as ev  # noqa: E402
import vehicle  # noqa: E402
import lab as dlab  # noqa: E402

LABS = ROOT / "replays" / "emblab"
FEAT = LABS / "feat"
# Never played: fall-holdout judges the drafts, the confirm suites judge what the lab deploys.
HOLDOUT = {"maps/fall-holdout", "maps/fresh-2918", "maps/fresh-2934"}
DEFAULTS = {
    "seed": 1, "p_force": 0.4, "pair_share": 0.0, "flip_ordinals": [0.6, 0.3, 0.1],
    "draft_mix": {"explore": 0.4, "ladder": 0.3, "night1": 0.3}, "explore_exclude": ["stellar"], "vehicles": 10, "threads": 94, "timeout": 900, "log_limit": 8 << 20, "night1": "research/night1-games.jsonl.gz",
}
NUM = re.compile(r"-?\d+(?:\.\d+)?(?:e-?\d+)?|x|nan|-?inf")


def log(lab, msg):
    dlab.log(lab, msg)


def init(args):
    lab = LABS / args.lab
    lab.mkdir(parents=True, exist_ok=True)
    cfg = {**DEFAULTS, **json.loads((lab / "config.json").read_text())} if (lab / "config.json").is_file() else dict(DEFAULTS)
    if args.source or "source" not in cfg:
        src = vehicle.freeze(args.source or "HEAD")
        cfg["source"] = src.relative_to(ROOT).as_posix()
        cfg["source_sha"] = vehicle.git("rev-parse", args.source or "HEAD")
    (lab / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")
    rows, seen = [], set()
    # Ladder maps first: some other sets hold copies of them.
    for f in sorted(FEAT.glob("*.jsonl"), key=lambda f: (f.stem != "ladder", f.stem)):
        for r in dlab.jsonl(f):
            if r["set"] in HOLDOUT or r["key"] in seen or f.stem == "test" or r["picks"] not in (3, 4, 5):
                continue
            seen.add(r["key"])
            rows.append(r)
    (lab / "maps.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    # The ladder prior: the top teams' compositions night1 sampled, in pick order, by frequency.
    import gzip
    comps = {p: collections.Counter() for p in (3, 4, 5)}
    with gzip.open(ROOT / cfg["night1"], "rt") as f:
        for line in f:
            g = json.loads(line)
            for s in "AB":
                if g.get(f"src{s}") == "ladder":
                    comps[len(g[s])][tuple(g[s])] += 1
    prior = {str(p): [[list(c), n] for c, n in comps[p].most_common()] for p in comps}
    # night1's Thompson teams per map: strong drafts under the old emblem logic.
    with gzip.open(ROOT / cfg["night1"], "rt") as f:
        for line in f:
            g = json.loads(line)
            for s in "AB":
                if g.get(f"src{s}") == "thompson" and g.get("draft_ok"):
                    prior.setdefault(g["key"], []).append(g[s])
    (lab / "prior.json").write_text(json.dumps(prior) + "\n")
    print(f"{len(rows)} maps by set: {dict(collections.Counter(r['set'] for r in rows))}")
    print(f"prior: {[(p, len(prior[p]), sum(n for _, n in prior[p])) for p in ('3', '4', '5')]}, night1 teams on {len(prior) - 3} maps; "
          f"source {cfg['source']}")


# ---------- plan ----------
def draw_team(r, picks, cfg, prior, key=None):
    mix = cfg["draft_mix"]
    u = r.random()
    if u < mix["explore"]:
        return r.sample([c for c in ev.CHAMPS if c not in cfg.get("explore_exclude", [])], picks), "explore"
    if u >= 1 - mix.get("night1", 0) and prior.get(key):
        return list(r.choice(prior[key])), "night1"
    comps = prior[str(picks)]
    return list(r.choices([c for c, _ in comps], weights=[n for _, n in comps])[0]), "ladder"


def rows_of(team):
    """The arm rows a team uses: pick i's, and Issac's (5) beside Cassi's."""
    return list(range(len(team))) + ([5] if "cassi_and_issac" in team else [])


def draw_arms(r, team, cfg):
    arms = [[ev.MODEL] * ev.ORDINALS for _ in range(6)]
    for row in rows_of(team):
        for k in range(ev.ORDINALS):
            if r.random() < cfg["p_force"]:
                arms[row][k] = r.choice(ev.ARMS)
    return arms


def flip(r, g, cfg):
    """g with one team's one (row, ordinal) changed: a model choice to a random arm, an arm to the model or another."""
    g = json.loads(json.dumps(g))
    side = r.choice("AB")
    row = r.choice(rows_of(g[side]))
    k = r.choices(range(len(cfg["flip_ordinals"])), weights=cfg["flip_ordinals"])[0]
    old = g[f"arms{side}"][row][k]
    new = r.choice(ev.ARMS) if old == ev.MODEL or r.random() < 0.5 else ev.MODEL
    while new == old:
        new = r.choice(ev.ARMS)
    g[f"arms{side}"][row][k] = new
    g["flip"] = {"side": side, "row": row, "k": k, "old": old, "new": new}
    return g


def plan(lab, cfg, b, games):
    r = random.Random(cfg["seed"] * 100003 + b)
    maps = dlab.jsonl(lab / "maps.jsonl")
    prior = json.loads((lab / "prior.json").read_text())
    V = cfg["vehicles"]
    ladder = [m for m in maps if m["set"] == "maps"]
    rest = [m for m in maps if m["set"] != "maps"]
    r.shuffle(rest)
    chosen = ladder + rest[:max(0, games // V - len(ladder))]
    out = []
    for m in chosen:
        for v in range(0, V, 2):
            g = {"map": m["path"], "key": m["key"], "set": m["set"], "picks": m["picks"]}
            for s in "AB":
                g[s], g[f"src{s}"] = draw_team(r, m["picks"], cfg, prior, m["key"])
                g[f"arms{s}"] = draw_arms(r, g[s], cfg)
            g["vehicle"] = v
            out.append(g)
            if v + 1 >= V:
                continue
            if r.random() < cfg["pair_share"]:
                h = flip(r, g, cfg)
                g["pair"] = h["pair"] = f"b{b:03d}-{len(out) - 1:05d}"
            else:
                h = {k: g[k] for k in ("map", "key", "set", "picks")}
                for s in "AB":
                    h[s], h[f"src{s}"] = draw_team(r, m["picks"], cfg, prior, m["key"])
                    h[f"arms{s}"] = draw_arms(r, h[s], cfg)
            h["vehicle"] = v + 1
            out.append(h)
    return {"batch": b, "games": out}


# ---------- extraction ----------
def emb_lines(path):
    """Per team: the EMB rows and the OOF line count, from a replay bundle's stdout."""
    out = {"emb": [[], []], "oof": [0, 0], "bytes": [0, 0]}
    try:
        with zipfile.ZipFile(path) as z:
            for t, team in enumerate("ab"):
                text = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                out["bytes"][t] = len(text)
                for line in text.splitlines():
                    if line.startswith("EMB "):
                        f = line.split()[1:]
                        head = [int(x) for x in f[:7]] + [float(x) for x in f[7:10]]
                        vals = [None if x == "x" else float(x) for x in f[10:]]
                        out["emb"][t].append(head + [vals])
                    elif line.startswith("OOF "):
                        out["oof"][t] += 1
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return path.name, out


def finish(lab, b, bdir, cfg, threads):
    p = json.loads((bdir / "plan.json").read_text())
    results = {r["stem"]: r for r in dlab.jsonl(bdir / "results.jsonl")}
    files = sorted(bdir.glob("*.repl26a"))
    embs = {}
    if files:
        with ProcessPoolExecutor(min(48, threads)) as ex:
            for name, o in ex.map(emb_lines, files, chunksize=16):
                embs[name.removesuffix(".repl26a")] = o
        with open(bdir / "emb.jsonl", "a") as f:
            f.write("".join(json.dumps({"stem": k, **v}) + "\n" for k, v in embs.items()))
        dlab.node(dlab.HERE / "outcome.mjs", bdir, "--out", bdir / "outcomes.jsonl", "--delete", "--threads", min(32, threads))
    embs = {r["stem"]: r for r in dlab.jsonl(bdir / "emb.jsonl")}
    outcomes = {r["file"].removesuffix(".repl26a"): r for r in dlab.jsonl(bdir / "outcomes.jsonl")}
    rows, decisions, bad = [], [], 0
    for i, g in enumerate(p["games"]):
        stem = f"g{i:05d}"
        res = results.get(stem)
        if res is None:
            continue
        gid = f"b{b:03d}-{stem}"
        row = {"id": gid, "batch": b, "bot": cfg["source_sha"][:10], **{k: v for k, v in g.items() if k != "vehicle_name"}}
        if res.get("error"):
            row["error"] = res["error"]
        else:
            row.update(winner=res["winner"], rounds=res["rounds"])
            o = outcomes.get(stem)
            if o:
                ids = [[vehicle.CHAMPS.index(c) for c in g[s]] for s in "AB"]
                row["draft_ok"] = o["draft"] == ids
                bad += not row["draft_ok"]
                end = o["cp"]["end"]
                row.update(wealth=[end[0][0] + end[0][1], end[1][0] + end[1][1]], cp=o["cp"], tributed=o["tributed"],
                           champions=o["champions"])
            e = embs.get(stem)
            if e:
                row.update(oof=e["oof"], stdout=e["bytes"], decisions=[len(e["emb"][0]), len(e["emb"][1])])
                for t in (0, 1):
                    for d in e["emb"][t]:
                        decisions.append({"id": gid, "team": t, "round": d[0], "type": d[1], "k": d[2], "arm": d[3], "chosen": d[4],
                                          "model": d[5], "gold": d[6], "str": d[7], "foc": d[8], "hp": d[9], "v": d[10]})
        rows.append(row)
    with open(lab / "games.jsonl", "a") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))
    with open(lab / "decisions.jsonl", "a") as f:
        f.write("".join(json.dumps(d) + "\n" for d in decisions))
    (bdir / "merged").write_text(f"{len(rows)}\n")
    errors = sum(1 for r in rows if r.get("error"))
    log(lab, f"batch {b}: merged {len(rows)} games ({errors} errors, {bad} draft mismatches), {len(decisions)} decisions")
    if bad > max(5, 0.02 * len(rows)):
        raise SystemExit(f"{bad} games drafted off the table: stopping")


# ---------- run ----------
def build(lab, cfg, b, p):
    source = ROOT / cfg["source"]
    per_vehicle = collections.defaultdict(list)
    for g in p["games"]:
        per_vehicle[g["vehicle"]] += [(g["key"], 0, g["A"], g["armsA"]), (g["key"], 1, g["B"], g["armsB"])]
    paths = []
    for v in range(cfg["vehicles"]):
        path, changed = ev.make(source, f"el-{lab.name}-v{v}", per_vehicle[v])
        if changed or not vehicle.built(path):
            paths.append(path)
    if paths:
        log(lab, f"batch {b}: built {len(paths)} vehicles in {vehicle.build_all(paths, par=len(paths)):.0f} s")
    for g in p["games"]:
        g["vehicle_name"] = f"el-{lab.name}-v{g['vehicle']}"


def run(args):
    lab = LABS / args.lab
    cfg = {**DEFAULTS, **json.loads((lab / "config.json").read_text())}
    for k in ("threads", "vehicles"):
        if getattr(args, k):
            cfg[k] = getattr(args, k)
    (lab / "batches").mkdir(exist_ok=True)
    for bdir in dlab.batch_dirs(lab):
        if not (bdir / "merged").is_file() and (bdir / "plan.json").is_file():
            log(lab, f"resuming {bdir.name}")
            p = json.loads((bdir / "plan.json").read_text())
            dlab.run_batch(bdir, p["games"], cfg["threads"], cfg["timeout"], cfg["log_limit"])
            finish(lab, int(bdir.name[1:]), bdir, cfg, cfg["threads"])
    for _ in range(args.batches):
        b = len(dlab.batch_dirs(lab))
        bdir = lab / "batches" / f"b{b:03d}"
        bdir.mkdir(parents=True)
        p = plan(lab, cfg, b, args.games)
        build(lab, cfg, b, p)
        (bdir / "plan.json").write_text(json.dumps(p))
        t0 = time.time()
        log(lab, f"batch {b}: {len(p['games'])} games")
        dlab.run_batch(bdir, p["games"], cfg["threads"], cfg["timeout"], cfg["log_limit"])
        log(lab, f"batch {b}: played in {time.time() - t0:.0f} s")
        finish(lab, b, bdir, cfg, cfg["threads"])


def status(args):
    lab = LABS / args.lab
    rows = dlab.jsonl(lab / "games.jsonl")
    ok = [r for r in rows if "winner" in r]
    print(f"{len(rows)} games, {len(rows) - len(ok)} errors, {sum(1 for r in ok if r.get('draft_ok') is False)} draft mismatches, "
          f"{sum(1 for r in ok if 'pair' in r)} in pairs")
    for line in (lab / "lab.log").read_text().splitlines()[-5:] if (lab / "lab.log").is_file() else []:
        print(line)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["init", "run", "status"])
    p.add_argument("--lab", required=True)
    p.add_argument("--source")
    p.add_argument("--games", type=int, default=12000)
    p.add_argument("--batches", type=int, default=1)
    p.add_argument("--threads", type=int)
    p.add_argument("--vehicles", type=int)
    args = p.parse_args()
    {"init": init, "run": run, "status": status}[args.command](args)


if __name__ == "__main__":
    main()
