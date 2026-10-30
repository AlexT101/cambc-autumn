"""Draft lab: learn which champions to draft from map features, pick count and the opponent's picks
(tools/draftlab/README.md).

    py tools/draftlab/lab.py init  --lab NAME [--source REF] [--top 10]   # freeze the bot, map features, ladder prior
    py tools/draftlab/lab.py run   --lab NAME --hours 8                   # batches until the deadline; resumes
    py tools/draftlab/lab.py fit   --lab NAME [--search]
    py tools/draftlab/lab.py report --lab NAME
    py tools/draftlab/lab.py status --lab NAME

Everything lives in replays/draftlab/NAME/: config.json, maps.jsonl, prior.json, ladder.jsonl, games.jsonl (one row
per finished game, never rewritten), model.json, report.md and batches/bNNN/."""
import argparse, collections, glob, json, os, re, shutil, subprocess, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
import vehicle  # noqa: E402
from run_batched import STATUS, REPLAY, ANSI, PER_GAME  # noqa: E402
import cpu_slots  # noqa: E402
import cambc_env  # noqa: E402
from fetch_replays import MY_TEAM  # noqa: E402

LABS = ROOT / "replays" / "draftlab"
# pool: globs of map files or directories; holdout: directories never played nor measured (judging what the lab
# deploys). prior_games / prior_maps: another lab's games and map table, fitted at prior_weight (never scored) so
# Thompson has a model from the first batch. features: the model's map features (model.mjs FEATURES names; init writes
# them all for null; a config without the key is a lab from before draft3, fitted on the first 19).
# Defaults: draft3 (tools/draftlab/PLAN-draft3.md): no prior, batch 0 explores, counters off (ctr 1e9) from the start.
# The pool is fresh suites no A/B has used (gen, gen-s1 and fresh-6003..6040 were); never fresh-9001..9004 or 9501..9520.
POOL = ["maps/*.map26a", "maps/fall-custom", "maps/fresh-91[0-9][0-9]", "maps/fresh-92[0-7][0-9]", "maps/fresh-9280"]
DEFAULTS = {
    "seed": 1, "pool": POOL,
    "holdout": [f"maps/fresh-{s}" for s in range(9300, 9380)], "pick_shares": {"3": 0.33, "4": 0.33, "5": 0.34},
    "mix": {"explore": 0.5, "thompson": 0.35, "probe": 0.15}, "ladder_opponent": 0.5, "thompson_draws": 16,
    "explore_batches": 1, "explore_exclude": ["stellar"], "search_batches": [1, 4, 9], "vehicles": 4,
    "batch_games": 40000, "threads": cpu_slots.SIZE, "patch_since": "2026-10-26T00:24", "timeout": 900,
    "prior_games": None, "prior_maps": None, "prior_weight": 0, "features": None,
    "initial_lam": {"b": 64, "w": 1280, "syn": 320, "ctr": 1e9, "side": 0.1}, "initial_alpha": 0,
}


# A fit keeps every game row in memory: past ~600k games Node's default heap is too small.
NODE_RUN_ENV = {**os.environ, "NODE_OPTIONS": os.environ.get("NODE_OPTIONS", "--max-old-space-size=65536")}


def node(*args, check=True):
    r = subprocess.run(["node", *map(str, args)], cwd=ROOT, text=True, encoding="utf-8", errors="replace",
                       capture_output=True, env=NODE_RUN_ENV)
    if r.stderr.strip():
        print(r.stderr.strip(), file=sys.stderr, flush=True)
    if check and r.returncode:
        raise RuntimeError(f"node {' '.join(map(str, args))} failed ({r.returncode})")
    return r.stdout.strip()


def jsonl(path):
    if not Path(path).is_file():
        return []
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def log(lab, msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(lab / "lab.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------- init ----------
def ladder_data(lab, cfg, top):
    """prior.json: the `top` best-rated other teams' compositions in pick order per pick count (any opponent; ours
    never: it models the opponents we meet), and ladder.jsonl: games between two of them or one of them and us, for
    model.mjs ladder's fit with team effects."""
    groups = []
    for f in glob.glob(str(ROOT / "replays" / "ladder" / "*" / "group.json")):
        g = json.loads(Path(f).read_text(encoding="utf-8"))
        if g["group"]["createdAt"] >= cfg["patch_since"] and g["group"].get("kind") == "ranked":
            groups.append(g)
    latest = {}
    for g in sorted(groups, key=lambda g: g["group"]["createdAt"]):
        for s in g["group"]["sides"]:
            latest[s["teamId"]] = (s.get("ratingAfter") or s.get("ratingBefore") or 0, s["teamName"])
    ranked = sorted(((t, v) for t, v in latest.items() if t != MY_TEAM), key=lambda kv: -kv[1][0])[:top]
    tops = {t for t, _ in ranked}
    playing = tops | {MY_TEAM}
    comps = {p: collections.Counter() for p in (3, 4, 5)}
    rows = []
    for g in groups:
        rating = {s["teamId"]: s.get("ratingBefore") for s in g["group"]["sides"]}
        for m in g["matches"]:
            sides = {s["side"]: s for s in m["sides"]}
            if m["status"] != "finished" or set(sides) != {"a", "b"}:
                continue
            drafts = {k: [vehicle.CHAMPS[int(i)] for i in s["draft"]] for k, s in sides.items()}
            for k, s in sides.items():
                p = len(drafts[k])
                if s["teamId"] in tops and p in comps and not s.get("botError"):
                    comps[p][tuple(drafts[k])] += 1
            a, b = sides["a"], sides["b"]
            if a["teamId"] in playing and b["teamId"] in playing and a["teamId"] != b["teamId"]:
                rows.append({"match": m["id"], "group": g["group"]["id"], "at": m["createdAt"], "map": m["map"],
                             "A": drafts["a"], "B": drafts["b"], "teamA": a["teamId"], "teamB": b["teamId"],
                             "ratingA": rating.get(a["teamId"]), "ratingB": rating.get(b["teamId"]),
                             "winner": 0 if a["result"] == "win" else 1, "scoreA": a.get("score"),
                             "scoreB": b.get("score"), "rounds": m.get("rounds")})
    prior = {p: [{"comp": list(c), "n": n} for c, n in comps[p].most_common() if n >= 2] for p in comps}
    prior["teams"] = [{"id": t, "name": n, "rating": r} for t, (r, n) in ranked]
    (lab / "prior.json").write_text(json.dumps(prior, indent=1, ensure_ascii=False), encoding="utf-8")
    (lab / "ladder.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return {p: sum(e["n"] for e in prior[p]) for p in comps}, len(rows), len(groups)


def all_features():
    return json.loads(node("--input-type=module", "-e", "import { FEATURES } from './tools/draftlab/model.mjs';"
                           " console.log(JSON.stringify(FEATURES.map(f => f[0])));"))


def pool_files(cfg):
    """The map files and directories of cfg's pool globs, less its holdout (shared with the emblem lab)."""
    held = {str(ROOT / h) for h in cfg["holdout"]}
    return [p for spec in cfg["pool"] for p in (sorted(glob.glob(str(ROOT / spec))) if glob.has_magic(spec) else [str(ROOT / spec)])
            if p not in held]


def write_maps(lab, cfg):
    print(node(HERE / "features.mjs", *pool_files(cfg), "--out", lab / "maps.jsonl"))


def init(args):
    lab = LABS / args.lab
    lab.mkdir(parents=True, exist_ok=True)
    cfg = {**DEFAULTS, **json.loads((lab / "config.json").read_text())} if (lab / "config.json").is_file() else dict(DEFAULTS)
    if args.source or "source" not in cfg:
        src = vehicle.freeze(args.source or "HEAD")
        cfg["source"] = src.relative_to(ROOT).as_posix()
        cfg["source_sha"] = vehicle.git("rev-parse", args.source or "HEAD")
    if cfg.get("features") is None:
        cfg["features"] = all_features()
    (lab / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")
    write_maps(lab, cfg)
    if cfg.get("prior_maps"):
        # The prior games' maps, for their features: set "prior:<set>", which plan never plays.
        rows = jsonl(lab / "maps.jsonl")
        keys = {r["key"] for r in rows}
        extra = [{**r, "set": f"prior:{r['set']}"} for r in jsonl(ROOT / cfg["prior_maps"]) if r["key"] not in keys]
        with open(lab / "maps.jsonl", "a", encoding="utf-8") as f:
            f.write("".join(json.dumps(r) + "\n" for r in extra))
        print(f"{len(extra)} prior maps added for {cfg['prior_games']}")
    teams, rows, groups = ladder_data(lab, cfg, args.top)
    print(f"prior from {groups} ranked groups since {cfg['patch_since']}: top-{args.top} opponents' team-games per pick count "
          f"{teams}; {rows} games among them and us in ladder.jsonl")
    print(f"source {cfg['source']} ({cfg['source_sha'][:8]})")
    if cfg.get("prior_games"):
        # No lab games yet to score a search on: fit at the prior lab's searched penalties.
        prev = Path(ROOT / cfg["prior_games"]).with_name("model.json")
        if prev.is_file():
            m = json.loads(prev.read_text())
            cfg["initial_lam"], cfg["initial_alpha"] = m["lam"], m.get("alpha", 0)
            (lab / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")
        print(node(HERE / "model.mjs", "fit", "--lab", lab))


# ---------- run ----------
def run_batch(bdir, games, threads, timeout, log_limit=0):
    """Plays the plan's games with cambc run-batch; returns {stem: result}, also appended to results.jsonl.
    Each game is its own run-batch holding a CPU slot (82 games/s on 96 cores, 2026-10-29; one run-batch
    for all of them tops out near 57, its parent's ~17 ms a game being serial), except on Windows
    (run_batched.PER_GAME)."""
    done = {r["stem"]: r for r in jsonl(bdir / "results.jsonl")}
    lines = {}
    for i, g in enumerate(games):
        stem = f"g{i:05d}"
        if stem not in done:
            v = (vehicle.VARIANTS / g["vehicle_name"]).as_posix()
            lines[stem] = f"{v} {v} {(ROOT / g['map']).as_posix()} {bdir.resolve().as_posix()}/{stem}.repl26a\n"
    if not lines:
        return done
    env = cambc_env.env()
    options = ["--color", "never", "--timeout", str(timeout), "--log-limit", str(log_limit)]
    lock = threading.Lock()

    def play(manifest, jobs):
        status = None
        with subprocess.Popen([vehicle.CAMBC, "run-batch", str(manifest), "--jobs", str(jobs), *options], cwd=bdir,
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                              errors="replace", bufsize=1) as proc:
            for raw in proc.stdout:
                line = ANSI.sub("", raw.rstrip("\r\n"))
                with lock:
                    rl.write(raw)
                if f := STATUS.match(line):
                    status = f
                    continue
                f = REPLAY.match(line)
                if not f or status is None:
                    continue
                stem = re.split(r"[\\/]", f.group(1))[-1].removesuffix(".repl26a")
                kind, team, failure, rounds = status.groups()
                status = None
                if kind == "STARTING":
                    continue
                r = {"stem": stem, "error": failure} if failure is not None else \
                    {"stem": stem, "winner": 0 if team == "A" else 1, "rounds": int(rounds or 0)}
                with lock:
                    done[stem] = r
                    out.write(json.dumps(r) + "\n")
                    out.flush()

    with open(bdir / "results.jsonl", "a", encoding="utf-8") as out, open(bdir / "run.log", "a", encoding="utf-8") as rl:
        if not PER_GAME:
            (bdir / "manifest.txt").write_text("".join(lines.values()), encoding="utf-8")
            play(bdir / "manifest.txt", threads)
            return done
        jobs = bdir / "jobs"
        jobs.mkdir(exist_ok=True)
        running = threading.BoundedSemaphore(threads)

        def one(stem, held):
            try:
                (jobs / f"{stem}.txt").write_text(lines[stem], encoding="utf-8")
                play(jobs / f"{stem}.txt", 1)
            finally:
                cpu_slots.release(held)
                running.release()

        for stem in lines:
            running.acquire()
            threading.Thread(target=one, args=(stem, cpu_slots.acquire(1, poll=0.05))).start()
        for _ in range(threads):
            running.acquire()
        shutil.rmtree(jobs, ignore_errors=True)
    return done


def merge(lab, b, bdir, plan, results, cfg):
    outcomes = {r["file"].removesuffix(".repl26a"): r for r in jsonl(bdir / "outcomes.jsonl")}
    rows, bad = [], 0
    for i, g in enumerate(plan["games"]):
        stem = f"g{i:05d}"
        r = results.get(stem)
        if r is None:
            continue
        row = {"id": f"b{b:03d}-{stem}", "batch": b, "bot": cfg["source_sha"][:10], **{k: v for k, v in g.items() if k != "vehicle_name"}}
        if r.get("error"):
            row["error"] = r["error"]
        else:
            row.update(winner=r["winner"], rounds=r["rounds"])
            o = outcomes.get(stem)
            if o:
                ids = [[vehicle.CHAMPS.index(c) for c in g[s]] for s in ("A", "B")]
                row["draft_ok"] = o["draft"] == ids
                bad += not row["draft_ok"]
                end = o["cp"]["end"]
                row.update(wealth=[end[0][0] + end[0][1], end[1][0] + end[1][1]], cp=o["cp"], tributed=o["tributed"],
                           champions=o["champions"])
        rows.append(row)
    with open(lab / "games.jsonl", "a", encoding="utf-8") as f:
        f.write("".join(json.dumps(r) + "\n" for r in rows))
    (bdir / "merged").write_text(f"{len(rows)}\n")
    return rows, bad


def batch_dirs(lab):
    return sorted((lab / "batches").glob("b[0-9][0-9][0-9]"))


def finish_batch(lab, b, bdir, cfg, threads):
    plan = json.loads((bdir / "plan.json").read_text())
    results = {r["stem"]: r for r in jsonl(bdir / "results.jsonl")}
    if any(bdir.glob("*.repl26a")):
        node(HERE / "outcome.mjs", bdir, "--out", bdir / "outcomes.jsonl", "--delete", "--threads", threads)
    rows, bad = merge(lab, b, bdir, plan, results, cfg)
    errors = sum(1 for r in rows if r.get("error"))
    log(lab, f"batch {b}: merged {len(rows)} games ({errors} errors, {bad} draft mismatches)")
    if bad > max(5, 0.02 * len(rows)):
        raise SystemExit(f"{bad} games drafted off the table: the vehicle's map key or table is wrong; stopping")


def fit_async(lab, search):
    args = ["node", str(HERE / "model.mjs"), "fit", "--lab", str(lab)] + (["--search"] if search else [])
    with open(lab / "fit.log", "a", encoding="utf-8") as f:
        f.write(f"\n== {time.strftime('%H:%M:%S')} {' '.join(args[2:])}\n")
        f.flush()
        # report after fit, in the same background shell.
        return subprocess.Popen(f'{subprocess.list2cmdline(args)} && node "{HERE / "model.mjs"}" report --lab "{lab}"',
                                cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, shell=True, env=NODE_RUN_ENV)


def run(args):
    lab = LABS / args.lab
    cfg = {**DEFAULTS, **json.loads((lab / "config.json").read_text())}
    for k in ("threads", "vehicles", "batch_games"):
        if getattr(args, k):
            cfg[k] = getattr(args, k)
    deadline = time.time() + args.hours * 3600
    (lab / "batches").mkdir(exist_ok=True)
    source = ROOT / cfg["source"]
    # Wall seconds per game at full threads, refined from each batch; it only stops a batch from running past the
    # deadline. draft2 played ~0.015 on 94 slots: 0.03 keeps batch 0 whole (0.45 cut it to ~35k games).
    per_game = 0.03
    fitting = None
    for bdir in batch_dirs(lab):
        if not (bdir / "merged").is_file() and (bdir / "plan.json").is_file():
            log(lab, f"resuming {bdir.name}")
            b = int(bdir.name[1:])
            plan = json.loads((bdir / "plan.json").read_text())
            run_batch(bdir, plan["games"], cfg["threads"], cfg["timeout"])
            finish_batch(lab, b, bdir, cfg, cfg["threads"])
    b = len(batch_dirs(lab))
    while True:
        left = deadline - time.time()
        games = min(cfg["batch_games"], int((left - 300) / per_game))
        if games < min(400, cfg["batch_games"]):
            break
        if fitting and fitting.poll() is None and not (lab / "model.json").is_file():
            fitting.wait()
        mode = "adapt" if b >= cfg["explore_batches"] and (lab / "model.json").is_file() else "explore"
        bdir = lab / "batches" / f"b{b:03d}"
        bdir.mkdir(parents=True, exist_ok=True)
        print(node(HERE / "model.mjs", "plan", "--lab", lab, "--batch", b, "--out", bdir / "plan.json", "--vehicles",
                   cfg["vehicles"], "--games", games, "--mode", mode))
        plan = json.loads((bdir / "plan.json").read_text())
        paths = []
        for k, entries in enumerate(plan["vehicles"]):
            path, changed = vehicle.make(source, f"dl-{args.lab}-v{k}", [(e["key"], e["team"], e["comp"]) for e in entries])
            if changed or not vehicle.built(path):
                paths.append(path)
        if paths:
            log(lab, f"batch {b}: built {len(paths)} vehicles in {vehicle.build_all(paths, par=len(paths)):.0f} s")
        for g in plan["games"]:
            g["vehicle_name"] = f"dl-{args.lab}-v{g['vehicle']}"
        (bdir / "plan.json").write_text(json.dumps(plan))
        t0 = time.time()
        log(lab, f"batch {b} ({mode}): {len(plan['games'])} games")
        run_batch(bdir, plan["games"], cfg["threads"], cfg["timeout"])
        per_game = max(0.01, (time.time() - t0) / max(1, len(plan["games"])))
        finish_batch(lab, b, bdir, cfg, cfg["threads"])
        log(lab, f"batch {b}: {per_game:.3f} s a game wall")
        if fitting and fitting.poll() is None:
            fitting.wait()
        fitting = fit_async(lab, b in cfg["search_batches"])
        b += 1
    if fitting:
        fitting.wait()
    log(lab, "deadline reached; final fit with search")
    fit_async(lab, True).wait()


def status(args):
    lab = LABS / args.lab
    rows = jsonl(lab / "games.jsonl")
    ok = [r for r in rows if "winner" in r]
    by = collections.Counter((r["picks"], r["srcA"] if r["srcA"] != "ladder" else r["srcB"]) for r in ok)
    print(f"{len(rows)} games, {len(rows) - len(ok)} errors, {sum(1 for r in ok if r.get('draft_ok') is False)} draft "
          f"mismatches, {sum(1 for r in ok if 'wealth' in r)} with outcomes")
    for p in (3, 4, 5):
        print(f"  {p} picks: {sum(n for (q, _), n in by.items() if q == p)}  " +
              ", ".join(f"{s} {n}" for (q, s), n in sorted(by.items()) if q == p))
    for line in (lab / "lab.log").read_text(encoding="utf-8").splitlines()[-5:] if (lab / "lab.log").is_file() else []:
        print(line)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["init", "run", "fit", "report", "status"])
    p.add_argument("--lab", required=True)
    p.add_argument("--source", help="git ref whose bots/astraeus the vehicles copy (init; default HEAD)")
    p.add_argument("--top", type=int, default=10, help="opponent teams in the ladder prior: the best-rated, ours left out")
    p.add_argument("--hours", type=float, default=8)
    p.add_argument("--threads", type=int)
    p.add_argument("--vehicles", type=int)
    p.add_argument("--batch-games", type=int)
    p.add_argument("--search", action="store_true")
    args = p.parse_args()
    if args.command == "init":
        init(args)
    elif args.command == "run":
        run(args)
    elif args.command == "status":
        status(args)
    else:
        lab = LABS / args.lab
        extra = ["--search"] if args.search and args.command == "fit" else []
        print(node(HERE / "model.mjs", args.command, "--lab", lab, *extra))


if __name__ == "__main__":
    main()
