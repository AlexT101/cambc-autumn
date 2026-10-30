"""Emblem lab: learn which emblems (and, with them, which drafts) win, from self-play games whose drafts and
emblem choices are randomised (tools/emblab/README.md).

    py tools/emblab/lab.py init   --lab NAME [--source REF]     # freeze REF's bots/astraeus, the map table, the prior
    py tools/emblab/lab.py run    --lab NAME --games 40000 [--batches N] [--vehicles 4] [--threads 94]
    py tools/emblab/lab.py status --lab NAME

Everything lives in replays/emblab/NAME/: config.json, maps.jsonl, prior.json, games.jsonl (one row per game),
decisions.jsonl (one row per logged emblem decision), lab.log and batches/bNNN/."""
import argparse, collections, itertools, json, random, re, subprocess, sys, time, zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
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
DEFAULTS = {
    # p_force[k]: the chance the k-th new emblem is drawn (mode 0); a uniform_share of team-games draw uniformly
    # (mode 1) at p_uniform instead. corr_model: the fit whose static gains steer mode 0's proposal.
    "seed": 1, "p_force": [0.35] + [0.5] * 11, "uniform_share": 0.1, "p_uniform": 0.2, "corr_model": "replays/emblab/main/model.json",
    "draft_mix": {"explore": 0.4, "ladder": 0.3, "night1": 0.3}, "explore_exclude": ["stellar"], "vehicles": 4, "threads": 94, "timeout": 900, "log_limit": 8 << 20, "night1": "research/night1-games.jsonl.gz",
    # holdout: sets never played (the suites that judge what the lab deploys). draft_lab (round 3 on): a draft lab
    # whose maps.jsonl is the pool (less its prior and holdout sets), whose prior.json gives the ladder compositions
    # and whose model.json the "model" teams (its deployed team per map); without it, replays/emblab/feat/ and night1.
    "holdout": [f"maps/fresh-{s}" for s in range(4041, 4045)], "draft_lab": None,
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
    if cfg.get("draft_lab"):
        init_from_draft_lab(lab, cfg)
        return
    held = set(cfg["holdout"])
    rows, seen = [], set()
    # Ladder maps first: some other sets hold copies of them.
    for f in sorted(FEAT.glob("*.jsonl"), key=lambda f: (f.stem != "ladder", f.stem)):
        for r in dlab.jsonl(f):
            if r["set"] in held or r["key"] in seen or f.stem == "test" or r["picks"] not in (3, 4, 5):
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


def init_from_draft_lab(lab, cfg):
    """maps.jsonl, and prior.json's ladder compositions and per-map teams (the draft lab model's deployed team), from
    cfg["draft_lab"]."""
    dl = ROOT / cfg["draft_lab"]
    held = set(cfg["holdout"]) | set(json.loads((dl / "config.json").read_text()).get("holdout", []))
    rows, seen = [], set()
    for r in dlab.jsonl(dl / "maps.jsonl"):
        if r["set"].startswith("prior:") or r["set"] in held or r["key"] in seen or r["picks"] not in (3, 4, 5):
            continue
        seen.add(r["key"])
        rows.append(r)
    (lab / "maps.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    pr = json.loads((dl / "prior.json").read_text())
    prior = {str(p): [[e["comp"], e["n"]] for e in pr.get(str(p), [])] for p in (3, 4, 5)}
    teams = 0
    if (dl / "model.json").is_file():
        for line in dlab.node(ROOT / "tools" / "draftlab" / "model.mjs", "teams", "--lab", dl, "--features", lab / "maps.jsonl").splitlines():
            key, _, _, team = line.split()
            if team != "-":
                prior[key] = [team.split(",")]
                teams += 1
    (lab / "prior.json").write_text(json.dumps(prior) + "\n")
    print(f"{len(rows)} maps by set: {dict(collections.Counter(r['set'] for r in rows))}")
    print(f"prior from {cfg['draft_lab']}: {[(p, len(prior[p]), sum(n for _, n in prior[p])) for p in ('3', '4', '5')]}, "
          f"model teams on {teams} maps; source {cfg['source']}")


# ---------- plan ----------
def draw_team(r, picks, cfg, prior, key=None):
    mix = cfg["draft_mix"]
    u = r.random()
    if u < mix["explore"]:
        return r.sample([c for c in ev.CHAMPS if c not in cfg.get("explore_exclude", [])], picks), "explore"
    # The per-map teams: the draft lab model's ("model"), or night1's Thompson teams.
    per_map = "model" if "model" in mix else "night1"
    if u >= 1 - mix.get(per_map, 0) and prior.get(key):
        return list(r.choice(prior[key])), per_map
    comps = prior[str(picks)]
    return list(r.choices([c for c, _ in comps], weights=[n for _, n in comps])[0]), "ladder"


def rows_of(team):
    """The arm rows a team uses: pick i's, and Issac's (5) beside Cassi's."""
    return list(range(len(team))) + ([5] if "cassi_and_issac" in team else [])


def draw_force(r, team, cfg):
    """(mode, seed, force): which of each arm row's first ORDINALS new emblems are drawn in the game, as bitmasks."""
    mode = 1 if r.random() < cfg["uniform_share"] else 0
    p = [cfg["p_uniform"]] * ev.ORDINALS if mode else cfg["p_force"]
    force = [0] * 6
    for row in rows_of(team):
        for k in range(ev.ORDINALS):
            if r.random() < p[k]:
                force[row] |= 1 << k
    return mode, r.getrandbits(32), force


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
        for v in range(V):
            g = {"map": m["path"], "key": m["key"], "set": m["set"], "picks": m["picks"], "vehicle": v}
            for s in "AB":
                g[s], g[f"src{s}"] = draw_team(r, m["picks"], cfg, prior, m["key"])
                g[f"mode{s}"], g[f"seed{s}"], g[f"force{s}"] = draw_force(r, g[s], cfg)
            out.append(g)
    return {"batch": b, "games": out}


# ---------- extraction ----------
INTS = ("round", "type", "k", "forced", "mode", "chosen", "base", "current")
STATE = ("own_gems", "enemy_gems", "carried", "alive", "picks")


def emb_lines(path, b):
    """Per team: the EMB row and OOF line counts from a replay bundle's stdout, and the game's decisions.jsonl
    rows, serialised here in the worker (~30 s a 40k batch in the parent)."""
    stem = path.name.removesuffix(".repl26a")
    out = {"stem": stem, "oof": [0, 0], "bytes": [0, 0], "decisions": [0, 0]}
    rows = []
    try:
        with zipfile.ZipFile(path) as z:
            for t, team in enumerate("ab"):
                text = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                out["bytes"][t] = len(text)
                for line in text.splitlines():
                    if line.startswith("EMB2 "):
                        f = line.split()[1:]
                        if len(f) != 18 + 42:  # cut off (the stdout cap, or the game's end)
                            continue
                        rows.append({"id": f"b{b:03d}-{stem}", "team": t, **{k: int(x) for k, x in zip(INTS, f[:8])}, "q": float(f[8]),
                                     "gold": int(f[9]), "str": float(f[10]), "foc": float(f[11]), "hp": float(f[12]),
                                     **{k: int(x) for k, x in zip(STATE, f[13:18])},
                                     "v": [None if x == "x" else float(x) for x in f[18:]]})
                        out["decisions"][t] += 1
                    elif line.startswith("OOF "):
                        out["oof"][t] += 1
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return out, "".join(json.dumps(r) + "\n" for r in rows).encode()


def finish(lab, b, bdir, cfg, threads):
    p = json.loads((bdir / "plan.json").read_text())
    results = {r["stem"]: r for r in dlab.jsonl(bdir / "results.jsonl")}
    files = sorted(bdir.glob("*.repl26a"))
    # emb.jsonl holds each game's counts and where its rows are in emb.dec, both kept for a resumed finish
    # (outcome.mjs deletes the replays).
    dec = bdir / "emb.dec"
    if files:
        at = dec.stat().st_size if dec.is_file() else 0
        with ProcessPoolExecutor(threads) as ex, open(bdir / "emb.jsonl", "a") as f, open(dec, "ab") as g:
            for o, text in ex.map(emb_lines, files, itertools.repeat(b), chunksize=16):
                o["at"] = [at, len(text)]
                at += len(text)
                g.write(text)
                f.write(json.dumps(o) + "\n")
        dlab.node(dlab.HERE / "outcome.mjs", bdir, "--out", bdir / "outcomes.jsonl", "--delete", "--threads", threads)
    embs = {r["stem"]: r for r in dlab.jsonl(bdir / "emb.jsonl")}
    blob = dec.read_bytes() if dec.is_file() else b""
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
                row.update(oof=e["oof"], stdout=e["bytes"], decisions=e["decisions"])
                decisions.append(blob[e["at"][0]:e["at"][0] + e["at"][1]])
        rows.append(row)
    with open(lab / "games.jsonl", "a") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))
    with open(lab / "decisions.jsonl", "ab") as f:
        f.write(b"".join(decisions))
    (bdir / "merged").write_text(f"{len(rows)}\n")
    errors = sum(1 for r in rows if r.get("error"))
    log(lab, f"batch {b}: merged {len(rows)} games ({errors} errors, {bad} draft mismatches), "
             f"{sum(sum(r.get('decisions', (0, 0))) for r in rows if 'winner' in r)} decisions")
    if bad > max(5, 0.02 * len(rows)):
        raise SystemExit(f"{bad} games drafted off the table: stopping")


# ---------- run ----------
def vehicle_name(lab, b, v):
    # Odd and even batches have their own vehicles, so building the next batch's never touches the playing one's.
    return f"el-{lab.name}-v{v}" + ("-odd" if b % 2 else "")


def build(lab, cfg, b, p):
    source = ROOT / cfg["source"]
    per_vehicle = collections.defaultdict(list)
    for g in p["games"]:
        per_vehicle[g["vehicle"]] += [(g["key"], t, g[s], g[f"mode{s}"], g[f"seed{s}"], g[f"force{s}"]) for t, s in enumerate("AB")]
    paths = []
    for v in sorted(per_vehicle):
        path, changed = ev.make(source, vehicle_name(lab, b, v), per_vehicle[v], cfg.get("corr_model"))
        if changed or not vehicle.built(path):
            paths.append(path)
    if paths:
        log(lab, f"batch {b}: built {len(paths)} vehicles in {vehicle.build_all(paths, par=len(paths)):.0f} s")
    for g in p["games"]:
        g["vehicle_name"] = vehicle_name(lab, b, g["vehicle"])


def prepare(lab, cfg, b, games):
    """Plan and build batch b; plan.json is written last, so only a fully built batch is ever resumed."""
    bdir = lab / "batches" / f"b{b:03d}"
    bdir.mkdir(parents=True)
    p = plan(lab, cfg, b, games)
    build(lab, cfg, b, p)
    (bdir / "plan.json").write_text(json.dumps(p))
    return bdir, p


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
            b = int(bdir.name[1:])
            p = json.loads((bdir / "plan.json").read_text())
            # Its vehicles may hold a later batch's tables by now.
            build(lab, cfg, b, p)
            dlab.run_batch(bdir, p["games"], cfg["threads"], cfg["timeout"], cfg["log_limit"])
            finish(lab, b, bdir, cfg, cfg["threads"])
    # Batch b plays while b - 1 finishes and b + 1 is planned and built, which would leave the cores idle.
    first = len(dlab.batch_dirs(lab))
    ready = prepare(lab, cfg, first, args.games) if args.batches else None
    played = None
    with ThreadPoolExecutor(1) as player:
        for b in range(first, first + args.batches):
            bdir, p = ready
            t0 = time.time()
            log(lab, f"batch {b}: {len(p['games'])} games")
            playing = player.submit(dlab.run_batch, bdir, p["games"], cfg["threads"], cfg["timeout"], cfg["log_limit"])
            if played:
                finish(lab, *played, cfg, cfg["threads"])
            ready = prepare(lab, cfg, b + 1, args.games) if b + 1 < first + args.batches else None
            playing.result()
            log(lab, f"batch {b}: played in {time.time() - t0:.0f} s")
            played = (b, bdir)
    if played:
        finish(lab, *played, cfg, cfg["threads"])


def status(args):
    lab = LABS / args.lab
    rows = dlab.jsonl(lab / "games.jsonl")
    ok = [r for r in rows if "winner" in r]
    print(f"{len(rows)} games, {len(rows) - len(ok)} errors, {sum(1 for r in ok if r.get('draft_ok') is False)} draft mismatches")
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
