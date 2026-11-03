"""Draft lab: learn which champions to draft from map features, pick count and the opponent's picks
(tools/draftlab/README.md).

    py tools/draftlab/lab.py init  --lab NAME [--source REF] [--top 10]   # freeze the bot, map features, ladder prior
    py tools/draftlab/lab.py run   --lab NAME --hours 8                   # batches until the deadline; resumes
    py tools/draftlab/lab.py fit   --lab NAME [--search]
    py tools/draftlab/lab.py report --lab NAME
    py tools/draftlab/lab.py status --lab NAME

Everything lives in replays/draftlab/NAME/: config.json, maps.jsonl, prior.json, ladder.jsonl, games.jsonl (one row
per finished game, never rewritten), model.json, report.md and batches/bNNN/."""
import argparse, collections, glob, json, os, re, shutil, subprocess, sys, tempfile, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
import vehicle  # noqa: E402
from run_batched import STATUS, REPLAY, ANSI, PER_GAME, is_fastrunner  # noqa: E402
import cpu_slots  # noqa: E402
import cambc_env  # noqa: E402
from fetch_replays import MY_TEAM  # noqa: E402

LABS = ROOT / "replays" / "draftlab"
# Twice an A/B's share of the CPU slots while both run (cpu_slots.py, fair share); the emblem lab imports this too.
os.environ.setdefault("CAMBC_SLOT_WEIGHT", "2")
PUBLISHED_SIZE = (29, 100)  # smallest and largest side of a published map
# pool: globs of map files or directories; holdout: directories never played nor measured (judging what the lab
# deploys). prior_games / prior_maps: another lab's games and map table, fitted at prior_weight (never scored) so
# Thompson has a model from the first batch. features: the model's map features (model.mjs FEATURES names; init writes
# them all for null; a config without the key is a lab from before draft3, fitted on the first 19).
# Defaults: draft3 (tools/draftlab/PLAN-draft3.md): no prior, batch 0 explores, counters off (ctr 1e9) from the start.
# From 2026-11-03 our side also plays "current" teams: the source bot's own draft (current_lab, read by init from its
# draft_model.h), in batch 0 (explore_mix) and after (mix).
# The pool is fresh suites no A/B or earlier lab has used: from 2026-11-03 fresh-77000..77195 (50,176 maps; draft3 and
# emblem round 3 played fresh-9100..9280). Never fresh-9001..9004 or 9501..9520.
POOL = ["maps/*.map26a", "maps/fall-custom", "maps/fresh-770[0-9][0-9]", "maps/fresh-771[0-8][0-9]", "maps/fresh-7719[0-5]"]
DEFAULTS = {
    "seed": 1, "pool": POOL,
    "holdout": [f"maps/fresh-{s}" for s in range(9300, 9380)], "pick_shares": {"3": 0.33, "4": 0.33, "5": 0.34},
    "mix": {"explore": 0.35, "current": 0.15, "thompson": 0.35, "probe": 0.15}, "explore_mix": {"explore": 0.6, "current": 0.4},
    "current_lab": None, "ladder_opponent": 0.5, "thompson_draws": 16,
    "explore_batches": 1, "explore_exclude": ["stellar"], "search_batches": [1, 4], "vehicles": 4,
    "batch_games": 100000, "fit_threads": 32, "plan_threads": 16, "outcome_threads": 16, "threads": cpu_slots.SIZE, "patch_since": "2026-10-26T00:24", "timeout": 900,
    "prior_games": None, "prior_maps": None, "prior_weight": 0, "features": None,
    "initial_lam": {"b": 256, "w": 1280, "syn": 320, "ctr": 1e9, "side": 0.1}, "initial_alpha": 0,
}


FASTRUNNER = ROOT / "tools" / "fastengine" / "runner" / "fastrunner"


def runner():
    """(cli, fast, env) for playing games. The fast runner by default (AGENTS.md; ~4.7x stock's games an hour,
    replays byte-identical): CAMBC_BIN if set, else tools/fastengine/runner/fastrunner when it answers, in native
    mode unless FASTRUNNER_MODE says otherwise. CAMBC_BIN=cambc plays on stock cambc."""
    cli = os.environ.get("CAMBC_BIN") or (str(FASTRUNNER) if FASTRUNNER.is_file() else vehicle.CAMBC)
    cli = shutil.which(cli) or cli
    fast = is_fastrunner(cli)
    env = cambc_env.env()
    if fast:
        env.setdefault("FASTRUNNER_MODE", "native")
    return cli, fast, env


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
    # Only published sizes (cambc-rules.yaml map.size): fall-custom's edge-case maps (7x3 to 256x256) stay on disk
    # for tests, out of the labs.
    rows = jsonl(lab / "maps.jsonl")
    keep = [r for r in rows if min(r["W"], r["H"]) >= PUBLISHED_SIZE[0] and max(r["W"], r["H"]) <= PUBLISHED_SIZE[1]]
    if len(keep) < len(rows):
        (lab / "maps.jsonl").write_text("".join(json.dumps(r) + "\n" for r in keep), encoding="utf-8")
        print(f"{len(rows) - len(keep)} maps outside the published sizes {PUBLISHED_SIZE} left out")


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
    if cfg.get("current_lab") is None:
        header = (ROOT / cfg["source"] / "src" / "draft" / "draft_model.h").read_text(encoding="utf-8")
        cfg["current_lab"] = re.search(r"model\.mjs cpp --lab (\S+?)[`\s]", header).group(1)
    if not (ROOT / cfg["current_lab"] / "model.json").is_file():
        raise SystemExit(f"current_lab {cfg['current_lab']} has no model.json (the source's draft): set current_lab")
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
    print(f"source {cfg['source']} ({cfg['source_sha'][:8]}); its draft (current teams) from {cfg['current_lab']}")
    if cfg.get("prior_games"):
        # No lab games yet to score a search on: fit at the prior lab's searched penalties.
        prev = Path(ROOT / cfg["prior_games"]).with_name("model.json")
        if prev.is_file():
            m = json.loads(prev.read_text())
            cfg["initial_lam"], cfg["initial_alpha"] = m["lam"], m.get("alpha", 0)
            (lab / "config.json").write_text(json.dumps(cfg, indent=1) + "\n")
        print(node(HERE / "model.mjs", "fit", "--lab", lab))


# ---------- run ----------
def run_batch(bdir, games, threads, timeout, log_limit=0, on_done=None):
    """Plays the plan's games with cambc run-batch; returns {stem: result}, also appended to results.jsonl.
    on_done(replay path) is called as each game ends without error.
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
    cli, fast, env = runner()
    options = ["--color", "never", "--timeout", str(timeout), "--log-limit", str(log_limit)]
    lock = threading.Lock()

    def play(manifest, jobs, extra=()):
        status = None
        # From the checkout (the fast runner needs its cambc.toml); every path in the manifest is absolute.
        with subprocess.Popen([cli, "run-batch", str(Path(manifest).resolve()), "--jobs", str(jobs), *options, *extra], cwd=ROOT,
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
                if on_done and failure is None:
                    on_done(bdir / f"{stem}.repl26a")

    with open(bdir / "results.jsonl", "a", encoding="utf-8") as out, open(bdir / "run.log", "a", encoding="utf-8") as rl:
        rl.write(f"runner {cli}{' (fastrunner, ' + env['FASTRUNNER_MODE'] + ')' if fast else ' (stock)'}\n")
        if fast:
            # One run-batch; it takes a CPU slot per game itself, so concurrent batches still share the machine.
            (bdir / "manifest.txt").write_text("".join(lines.values()), encoding="utf-8")
            play(bdir / "manifest.txt", threads, ["--slot-dir", str(cpu_slots.DIR), "--slots", str(cpu_slots.SIZE)])
            return done
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


# games.slim.jsonl: the fields model.mjs reads (readGames) of games.jsonl's first `bytes`, ~8x smaller than its
# ~3 KB a game; games.slim.json holds {bytes, slim_bytes}. model.mjs reads games.jsonl past `bytes` in full, so a
# slim file behind games.jsonl is only slower. Delete both to rebuild.
SLIM = ("id", "batch", "key", "picks", "A", "B", "srcA", "srcB", "winner", "wealth", "draft_ok", "error")
SLIM_CHAMP = ("type", "team", "carried", "collectedGems", "submittedGems", "deaths", "kills", "monsterDamageDone",
              "monsterDamageTaken")


def update_slim(lab):
    games, slim, meta_file = lab / "games.jsonl", lab / "games.slim.jsonl", lab / "games.slim.json"
    if not games.is_file():
        return
    meta = json.loads(meta_file.read_text()) if meta_file.is_file() else {"bytes": 0, "slim_bytes": 0}
    if meta["bytes"] > games.stat().st_size:  # games.jsonl was rewritten
        meta = {"bytes": 0, "slim_bytes": 0}
    if meta["bytes"] == games.stat().st_size:
        return
    with open(games, "rb") as f, open(slim, "r+b" if slim.is_file() else "w+b") as out:
        out.truncate(meta["slim_bytes"])  # past it: a cut-short update's
        out.seek(meta["slim_bytes"])
        f.seek(meta["bytes"])
        done = meta["bytes"]
        for line in f:
            if not line.endswith(b"\n"):
                break
            done += len(line)
            if line.strip():
                g = json.loads(line)
                row = {k: g[k] for k in SLIM if k in g}
                if "champions" in g:
                    row["ch"] = [[c.get(k) for k in SLIM_CHAMP] for c in g["champions"]]
                out.write((json.dumps(row, separators=(",", ":")) + "\n").encode())
        meta = {"bytes": done, "slim_bytes": out.tell()}
    tmp = lab / "games.slim.json.tmp"
    tmp.write_text(json.dumps(meta))
    tmp.replace(meta_file)


def batch_dirs(lab):
    return sorted((lab / "batches").glob("b[0-9][0-9][0-9]"))


class OutcomeFeed:
    """outcome.mjs --stdin on `threads` workers, reading each replay as its game ends (run_batch on_done), so a
    batch's outcomes are ready when its last game is (draft4 spent ~115 s a 100k batch reading them afterwards, on
    the critical path to the next fit). Replays it does not get to stay for finish_batch."""

    def __init__(self, bdir, threads):
        self.lock = threading.Lock()
        self.log = open(bdir / "outcome.log", "a", encoding="utf-8")
        self.proc = subprocess.Popen(["node", str(HERE / "outcome.mjs"), "--stdin", "--out", str(bdir / "outcomes.jsonl"), "--delete",
                                      "--threads", str(threads)], cwd=ROOT, stdin=subprocess.PIPE, stdout=self.log,
                                     stderr=subprocess.STDOUT, text=True, env=NODE_RUN_ENV)

    def add(self, replay):
        with self.lock:
            try:
                self.proc.stdin.write(f"{replay}\n")
                self.proc.stdin.flush()
            except OSError:  # it died: finish_batch reads what is left
                pass

    def close(self):
        with self.lock:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        self.proc.wait()
        self.log.close()


def finish_batch(lab, b, bdir, cfg, threads):
    plan = json.loads((bdir / "plan.json").read_text())
    results = {r["stem"]: r for r in jsonl(bdir / "results.jsonl")}
    if any(bdir.glob("*.repl26a")):
        node(HERE / "outcome.mjs", bdir, "--out", bdir / "outcomes.jsonl", "--delete", "--threads", threads)
    rows, bad = merge(lab, b, bdir, plan, results, cfg)
    update_slim(lab)
    errors = sum(1 for r in rows if r.get("error"))
    log(lab, f"batch {b}: merged {len(rows)} games ({errors} errors, {bad} draft mismatches)")
    if bad > max(5, 0.02 * len(rows)):
        raise SystemExit(f"{bad} games drafted off the table: the vehicle's map key or table is wrong; stopping")


class FitJob:
    """model.mjs fit in the background on up to `slots` CPU slots from the pool, one worker thread each (model.mjs
    startPool), so the fit's threads take cores from games rather than crowding them; the lab's own games hand the
    slots over as they end. poll() and wait() as Popen's. Then its report, which nothing waits for (the next plan
    reads model.json only) but wait_report(); a newer fit's report replaces a running one."""
    report = None

    def __init__(self, lab, search, slots):
        self.code, self.done = None, threading.Event()
        threading.Thread(target=self._run, args=(lab, search, slots), daemon=True).start()

    def _run(self, lab, search, slots):
        try:
            held = cpu_slots.acquire(slots, least=min(slots, 16), poll=0.005)
            try:
                args = ["node", str(HERE / "model.mjs"), "fit", "--lab", str(lab), "--threads", str(len(held))] + (["--search"] if search else [])
                with open(lab / "fit.log", "a", encoding="utf-8") as f:
                    f.write(f"\n== {time.strftime('%H:%M:%S')} {' '.join(args[2:])}\n")
                    f.flush()
                    self.code = subprocess.run(args, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, env=NODE_RUN_ENV).returncode
            finally:
                cpu_slots.release(held)
            if self.code == 0:
                if FitJob.report and FitJob.report.poll() is None:
                    FitJob.report.kill()
                with open(lab / "fit.log", "a", encoding="utf-8") as f:
                    FitJob.report = subprocess.Popen(["node", str(HERE / "model.mjs"), "report", "--lab", str(lab)], cwd=ROOT,
                                                     stdout=f, stderr=subprocess.STDOUT, env=NODE_RUN_ENV)
        finally:
            self.done.set()

    def poll(self):
        return self.code if self.done.is_set() else None

    def wait(self):
        self.done.wait()
        return self.code

    @staticmethod
    def wait_report():
        return FitJob.report.wait() if FitJob.report else None


def fit_async(lab, search, slots=32):
    return FitJob(lab, search, slots)


def vehicle_names(lab_name, b, plan, cfg):
    """Batch b's vehicles: two sets by parity, so one batch's vehicles build while the other's play. Plans from before
    the overlap name theirs in games' vehicle_name (dl-<lab>-v<k>)."""
    if "vehicle_names" in plan:
        return plan["vehicle_names"]
    return [f"dl-{lab_name}-{'v' if b % 2 == 0 else 'w'}{k}" for k in range(len(plan["vehicles"]))]


def ensure_vehicles(lab, b, plan, names, source):
    """Writes and builds the plan's vehicles (unchanged ones keep their build), then compiles them for the fast
    runner's native mode with one round each, so the batch's first games don't wait for it."""
    paths = []
    for name, entries in zip(names, plan["vehicles"]):
        path, changed = vehicle.make(source, name, [(e["key"], e["team"], e["comp"]) for e in entries])
        if changed or not vehicle.built(path):
            paths.append(path)
    if paths:
        log(lab, f"batch {b}: built {len(paths)} vehicles in {vehicle.build_all(paths, par=len(paths)):.0f} s")
    cli, fast, env = runner()
    if fast and env.get("FASTRUNNER_MODE") == "native" and paths and plan["games"]:
        t0 = time.time()
        with tempfile.TemporaryDirectory() as tmp:
            game = plan["games"][0]
            manifest = Path(tmp) / "warm.txt"
            manifest.write_text("".join(f"{Path(p).as_posix()} {Path(p).as_posix()} {(ROOT / game['map']).as_posix()} {tmp}/w{i}.repl26a\n"
                                        for i, p in enumerate(paths)))
            subprocess.run([cli, "run-batch", str(manifest), "--rounds", "1", "--jobs", str(len(paths)), "--log-limit", "0"],
                           cwd=ROOT, env=env, capture_output=True)
        log(lab, f"batch {b}: native compile {time.time() - t0:.0f} s")


def prepare(lab, b, games, cfg, source, exclude=()):
    """Plans batch b (games skip the unmerged batches in `exclude`) and builds its vehicles; marks it ready."""
    mode = "adapt" if b >= cfg["explore_batches"] and (lab / "model.json").is_file() else "explore"
    bdir = lab / "batches" / f"b{b:03d}"
    bdir.mkdir(parents=True, exist_ok=True)
    extra = ["--exclude", ",".join(str(x / "plan.json") for x in exclude)] if exclude else []
    # The plan's Thompson draws on worker threads, on slots from the pool (the games playing meanwhile hand them over).
    held = cpu_slots.acquire(cfg["plan_threads"], least=cfg["plan_threads"], poll=0.005)
    try:
        print(node(HERE / "model.mjs", "plan", "--lab", lab, "--batch", b, "--out", bdir / "plan.json", "--vehicles",
                   cfg["vehicles"], "--games", games, "--mode", mode, "--threads", len(held), *extra))
    finally:
        cpu_slots.release(held)
    plan = json.loads((bdir / "plan.json").read_text())
    names = vehicle_names(lab.name, b, plan, cfg)
    plan["vehicle_names"] = names
    for g in plan["games"]:
        g["vehicle_name"] = names[g["vehicle"]]
    (bdir / "plan.json").write_text(json.dumps(plan))
    ensure_vehicles(lab, b, plan, names, source)
    (bdir / "ready").write_text(mode + "\n")
    return bdir, mode


def run(args):
    """Batches back to back: while batch b plays, a thread merges batch b-1, refits and prepares batch b+1 (plan,
    vehicles, native compile), so the CPU slots never wait on the lab's own bookkeeping."""
    lab = LABS / args.lab
    cfg = {**DEFAULTS, **json.loads((lab / "config.json").read_text())}
    for k in ("threads", "vehicles", "batch_games"):
        if getattr(args, k):
            cfg[k] = getattr(args, k)
    deadline = time.time() + args.hours * 3600
    (lab / "batches").mkdir(exist_ok=True)
    update_slim(lab)
    cli, fast, env = runner()
    log(lab, f"runner {cli}: " + (f"fastrunner, {env['FASTRUNNER_MODE']}" if fast else "STOCK cambc (~4.7x slower than the fast runner)"))
    source = ROOT / cfg["source"]
    # Wall seconds per game at full threads, refined from each batch; it only stops a batch from running past the
    # deadline, and sizes batch 1 before any game has ended. draft2 played ~0.015 on 94 slots on stock: 0.03 kept batch 0
    # whole (0.45 cut it to ~35k games); draft4 on the fast runner played 0.0023-0.0035, and its 0.03 cut batch 1 to 68k.
    per_game = 0.005 if fast else 0.03
    state = {"fitting": None, "pending_search": False}

    def fit_after(b):
        """A fit with batch b's games, unless one is running (the next fit then includes them; a search asked for
        meanwhile waits for it). Waits for a plain fit, so the next plan uses it, and always when there is no model."""
        state["pending_search"] |= b in cfg["search_batches"]
        f = state["fitting"]
        if f and f.poll() is None:
            if not (lab / "model.json").is_file():
                f.wait()
            return
        search, state["pending_search"] = state["pending_search"], False
        state["fitting"] = f = fit_async(lab, search, cfg["fit_threads"])
        if not search or not (lab / "model.json").is_file():
            f.wait()

    def play(b, bdir):
        plan = json.loads((bdir / "plan.json").read_text())
        log(lab, f"batch {b} ({(bdir / 'ready').read_text().strip() if (bdir / 'ready').is_file() else 'resumed'}): {len(plan['games'])} games")
        t0 = time.time()
        feed = OutcomeFeed(bdir, cfg["outcome_threads"])
        try:
            run_batch(bdir, plan["games"], cfg["threads"], cfg["timeout"], on_done=feed.add)
        finally:
            feed.close()
        return max(0.005, (time.time() - t0) / max(1, len(plan["games"])))

    # Resume: batches planned but not merged play in order; a batch whose preparation was cut short is planned again.
    for bdir in batch_dirs(lab):
        if (bdir / "merged").is_file():
            continue
        if not (bdir / "plan.json").is_file() or not ((bdir / "ready").is_file() or (bdir / "results.jsonl").is_file()):
            log(lab, f"{bdir.name} was not ready: planning it again")
            shutil.rmtree(bdir)
            continue
        b = int(bdir.name[1:])
        log(lab, f"resuming {bdir.name}")
        plan = json.loads((bdir / "plan.json").read_text())
        ensure_vehicles(lab, b, plan, vehicle_names(lab.name, b, plan, cfg), source)
        play(b, bdir)
        finish_batch(lab, b, bdir, cfg, cfg["threads"])
        fit_after(b)

    def size(start):
        """Games for a batch starting at `start` (an estimate), or 0 past the deadline."""
        games = min(cfg["batch_games"], int((deadline - start - 300) / per_game))
        return games if games >= min(400, cfg["batch_games"]) else 0

    b = len(batch_dirs(lab))
    games = size(time.time())
    current = prepare(lab, b, games, cfg, source)[0] if games else None
    while current:
        after = {"next": None, "error": None}
        t_start = time.time()
        plan_games = len(json.loads((current / "plan.json").read_text())["games"])

        def background(b=b, current=current, prev=b - 1, t_start=t_start, plan_games=plan_games):
            try:
                pdir = lab / "batches" / f"b{prev:03d}"
                if prev >= 0 and pdir.is_dir() and not (pdir / "merged").is_file():
                    finish_batch(lab, prev, pdir, cfg, cfg["threads"])
                    fit_after(prev)
                n = size(t_start + plan_games * per_game)
                if n:
                    after["next"] = prepare(lab, b + 1, n, cfg, source, exclude=[current])[0]
            except BaseException as e:  # noqa: BLE001 - re-raised in the main thread
                after["error"] = e

        worker = threading.Thread(target=background, daemon=True)
        worker.start()
        per_game = play(b, current)
        log(lab, f"batch {b}: {per_game:.3f} s a game wall")
        t_wait = time.time()
        worker.join()
        if time.time() - t_wait > 5:
            log(lab, f"batch {b}: waited {time.time() - t_wait:.0f} s for batch {b + 1}'s preparation")
        if after["error"]:
            raise after["error"]
        current, b = after["next"], b + 1
    # The last batch played: merge it, then the final fit.
    last = lab / "batches" / f"b{b - 1:03d}"
    if b > 0 and last.is_dir() and not (last / "merged").is_file():
        finish_batch(lab, b - 1, last, cfg, cfg["threads"])
    if state["fitting"]:
        state["fitting"].wait()
    log(lab, "deadline reached; final fit with search")
    fit_async(lab, True, cfg["fit_threads"]).wait()
    FitJob.wait_report()


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
        update_slim(lab)
        extra = ["--search"] if args.search and args.command == "fit" else []
        print(node(HERE / "model.mjs", args.command, "--lab", lab, *extra))


if __name__ == "__main__":
    main()
