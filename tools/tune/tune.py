"""SPSA tuning of a bot's constants against a panel of opponents, on the fast runner with no compiles.

    py tools/tune/tune.py init --run NAME --bot bots/archives/diana --opps variants/astraeus-fc99b84,baselines/v67 [--pool ...]
    py tools/tune/tune.py run --run NAME [--hours H | --iters N]      # resumes; Ctrl-C or kill is safe between batches
    py tools/tune/tune.py status --run NAME                            # iterations, the current values, recent scores
    py tools/tune/tune.py apply --run NAME --out bots/diana-t1          # a copy of the bot with the current values built in
    py tools/tune/tune.py play --run NAME --values a.json --games N      # one scored batch of fixed values (default: current)

The bot must be tunified first (research/diana-2026-11-03/tunify.py: the chosen params.h constants read one block
behind a magic). Each candidate is the base build with that block rewritten in its wasm and in the fast runner's
cached native library and wasmtime module (patch.py), so a candidate costs no compile; its games are byte-identical
to a fresh build's.

An iteration: `pairs` random sign vectors D; each pair plays x + c D and x - c D (x: the values scaled to [0, 1]
over each range), all candidates on the same games (maps drawn from the pool, every opponent, random sides), in one
fast-runner run-batch that holds a CPU slot per game (tools/cpu_slots.py, fair-shared with other jobs). A game scores
w_win * (+1 win, -1 loss, 0 draw) + w_gems * (ours - theirs) / (ours + theirs) of tributed gems + w_gold * the same of
earned gold, balanced around 0. x moves by a_k times the mean of (f+ - f-) / (2 c_k) D. Ints are rounded when played.

State is replays/tune/NAME/: config.json (editable: ranges, gains, games), state.json, history.jsonl (one line per
iteration: scores, x) and games.jsonl (one line per iteration: names, its sign vectors `deltas` and per-name c_k `cn`
in that order, `games` as [map, opponent, side (0: we are team A)], and each candidate's score per game, null if it
failed). Each iteration's replays are in work/itK, deleted once scored unless TUNE_KEEP is set.
"""
import argparse, json, math, os, random, re, shutil, subprocess, sys, time, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cambc_env  # noqa: E402
import cpu_slots  # noqa: E402
import patch  # noqa: E402

RUNS = ROOT / "replays" / "tune"
FASTRUNNER = ROOT / "tools" / "fastengine" / "runner" / "fastrunner"
DEFAULT_POOL = ["maps", "maps/gen", "maps/gen-s1"] + [f"maps/suites/fresh/fresh-{s}" for s in range(92001, 92101)]
STATUS = re.compile(r"^\[.\] (TEAM ([AB]) WIN|FAILED: (.*?))  ")


def log(run, msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with (run / "tune.log").open("a") as f:
        f.write(line + "\n")


def copy_bot(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".cambc"))


def build_release(bot: Path):
    r = subprocess.run(["cambc", "build", str(bot), "--release"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"building {bot} failed:\n{r.stdout[-3000:]}{r.stderr[-3000:]}")


def ranges_for(spec):
    """Default search ranges: half to double each default (fractions capped below 1), ints at least +-2."""
    out = {}
    for n, d in spec["floats"]:
        lo, hi = d * 0.5, d * 2.0
        if 0 < d < 1 and any(k in n for k in ("fraction", "share", "risk")):
            hi = min(hi, 0.95)
        out[n] = [round(lo, 4), round(hi, 4), "float"]
    for n, d in spec["ints"]:
        lo, hi = min(d - 2, math.floor(d * 0.5)), max(d + 2, math.ceil(d * 2))
        out[n] = [max(0, lo), hi, "int"]
    return out


def maps_in(pool):
    maps = []
    for d in pool:
        p = ROOT / d
        maps += sorted(p.glob("*.map26a")) if p.is_dir() else []
    return maps


def cmd_init(a):
    run = RUNS / a.run
    if (run / "config.json").exists() and not a.force:
        raise SystemExit(f"{run} exists (--force replaces its config, keeping nothing else)")
    if run.exists() and a.force:
        shutil.rmtree(run)
    run.mkdir(parents=True)
    bot = (ROOT / a.bot).resolve() if not Path(a.bot).is_absolute() else Path(a.bot)
    copy_bot(bot, run / "base")
    opps = []
    for o in a.opps.split(","):
        src = ROOT / "bots" / o
        if not src.is_dir():
            raise SystemExit(f"no bot {src}")
        name = o.replace("/", "-")
        copy_bot(src, run / "opps" / name)
        opps.append(name)
    with ThreadPoolExecutor(len(opps)) as pool:
        list(pool.map(lambda n: build_release(run / "opps" / n), opps))
    build_release(run / "base")
    spec = json.loads((run / "base" / "src" / "tune.json").read_text())
    params = a.params.split(",") if a.params else [n for n, _ in spec["floats"] + spec["ints"]]
    rng = ranges_for(spec)
    cfg = {
        "bot": a.bot, "opps": opps, "pool": a.pool.split(",") if a.pool else DEFAULT_POOL,
        "params": {n: rng[n] for n in params},
        "maps_per_iter": a.maps, "pairs": a.pairs, "weights": {"win": 0.7, "gems": 0.2, "gold": 0.1},
        # SPSA gains in the [0, 1] scaled space: a_k = a / (k + 1 + A)^alpha, c_k = c / (k + 1)^gamma.
        "a": 0.15, "A": 20, "alpha": 0.602, "c": 0.12, "gamma": 0.101, "seed": a.seed,
    }
    (run / "config.json").write_text(json.dumps(cfg, indent=1))
    base = patch.Base(run / "base")
    d = base.defaults()
    x = {n: (d[n] - lo) / (hi - lo) for n, (lo, hi, _) in cfg["params"].items()}
    (run / "state.json").write_text(json.dumps({"k": 0, "x": x}, indent=1))
    # One game caches the base's native library and wasmtime module, which candidates are patched from.
    warm(run, base)
    print(f"{run}: {len(params)} params, {len(opps)} opponents, {len(maps_in(cfg['pool']))} pool maps")


def runner_env(run):
    env = dict(os.environ, FASTRUNNER_MODE=os.environ.get("FASTRUNNER_MODE", "native"), FASTRUNNER_BUILT="1",
               CAMBC_SLOT_GROUP=os.environ.get("CAMBC_SLOT_GROUP", f"tune-{run.name}"))
    env.pop("LD_PRELOAD", None)
    return env


def warm(run, base):
    if len(base.cached) >= 2:
        return
    tmp = run / "warm"
    tmp.mkdir(exist_ok=True)
    m = next(iter(sorted((ROOT / "maps").glob("*.map26a"))))
    (tmp / "m.txt").write_text(f"{run / 'base'} {run / 'base'} {m} {tmp / 'w.repl26a'}\n")
    subprocess.run([str(FASTRUNNER), "run-batch", str(tmp / "m.txt"), "--jobs", "1", "--release", "--rounds", "1"],
                   cwd=ROOT, env=runner_env(run), capture_output=True)
    shutil.rmtree(tmp, ignore_errors=True)
    base.__init__(run / "base")
    if len(base.cached) < 2:
        raise SystemExit(f"the base's native library and wasmtime module were not cached ({list(base.cached)})")


def values_of(cfg, x):
    out = {}
    for n, (lo, hi, kind) in cfg["params"].items():
        v = lo + min(1.0, max(0.0, x[n])) * (hi - lo)
        out[n] = int(round(v)) if kind == "int" else v
    return out


LOG_LIMIT = 4096


def summarize(camstat: Path):
    r = subprocess.run(["cambc", "summary", str(camstat), "-o", "-"], capture_output=True, text=True)
    if r.returncode:
        return None
    s = json.loads(r.stdout)
    gems = {t["team"]: float(t.get("submittedGems", 0)) for t in s["teams"]}
    gold = {"teamA": 0.0, "teamB": 0.0}
    for tl in s["championTimelines"]:
        if tl["metric"] == "earnedGold" and tl["runs"]:
            gold[tl["owner"]["team"]] += float(tl["runs"][-1]["value"])
    # Local builds' draft lines (cambc_env.LOCAL_HEADER) are their first output: run-batch keeps LOG_LIMIT bytes.
    capped = {}
    try:
        with zipfile.ZipFile(camstat.with_suffix(".repl26a")) as z:
            for team in "ab":
                out = z.read(f"team-{team}.stdout").translate(None, b"\0")
                capped["team" + team.upper()] = out.startswith(b"DRAFT-CAPPED") or b"\nDRAFT-CAPPED" in out
    except (OSError, KeyError, zipfile.BadZipFile):
        pass
    return {"outcome": s["match"].get("outcome"), "rounds": s["match"].get("roundsCompleted"), "gems": gems, "gold": gold,
            "capped": capped}


def margin(ours, theirs):
    return (ours - theirs) / (ours + theirs) if ours + theirs > 0 else 0.0


def score(w, res, side):
    us, them = ("teamA", "teamB") if side == 0 else ("teamB", "teamA")
    win = 1.0 if res["outcome"] == us else -1.0 if res["outcome"] == them else 0.0
    return (w["win"] * win + w["gems"] * margin(res["gems"][us], res["gems"][them])
            + w["gold"] * margin(res["gold"][us], res["gold"][them])), win


class Batch:
    """One run-batch of every candidate on the same games, started in the background (start) and scored (finish)."""

    def __init__(self, run, cfg, cands, games, tag, base=None):
        self.run, self.cfg, self.cands, self.games, self.tag = run, cfg, cands, games, tag
        base = base or patch.Base(run / "base")
        self.work = run / "work" / tag
        shutil.rmtree(self.work, ignore_errors=True)
        self.work.mkdir(parents=True)
        dirs, self.hashes = {}, set()
        with ThreadPoolExecutor(min(8, len(cands))) as pool:
            for name, (path, h) in zip(cands, pool.map(lambda nv: base.write(nv[1], self.work / "bots" / nv[0]), cands.items())):
                dirs[name] = path
                if h != base.hash:
                    self.hashes.add(h)
        lines, self.meta = [], {}
        for name in cands:
            for gi, (m, opp, side) in enumerate(games):
                a, b = (dirs[name], run / "opps" / opp) if side == 0 else (run / "opps" / opp, dirs[name])
                stem = f"{name}-{gi}"
                self.meta[stem] = (name, gi, side)
                lines.append(f"{a} {b} {m} {self.work / (stem + '.repl26a')} --statistics {self.work / (stem + '.camstat')}\n")
        random.Random(tag).shuffle(lines)
        (self.work / "manifest.txt").write_text("".join(lines))
        self.n = len(lines)

    def start(self):
        self.t0 = time.time()
        self.out = (self.work / "run.log").open("w")
        self.proc = subprocess.Popen([str(FASTRUNNER), "run-batch", str(self.work / "manifest.txt"), "--release", "--log-limit", str(LOG_LIMIT),
                                      "--jobs", str(min(self.n, cpu_slots.SIZE)), "--slot-dir", str(cpu_slots.DIR),
                                      "--slots", str(cpu_slots.SIZE)], cwd=ROOT, env=runner_env(self.run), stdout=self.out,
                                     stderr=subprocess.STDOUT)
        return self

    def wait(self):
        self.proc.wait()
        self.wall = time.time() - self.t0
        self.out.close()

    def finish(self):
        """{name: [(score, win, game index)]}; deletes the batch's files and its candidates' cache entries."""
        stems = list(self.meta)
        with ThreadPoolExecutor(32) as pool:
            stats = list(pool.map(lambda s: summarize(self.work / (s + ".camstat")), stems))
        res = {name: [] for name in self.cands}
        failed = 0
        early = {"candidates": 0, "opponents": 0}
        capped = {"candidates": 0, "opponents": 0}
        for s, st in zip(stems, stats):
            name, gi, side = self.meta[s]
            if st is None:
                failed += 1
                continue
            sc, win = score(self.cfg["weights"], st, side)
            if st["rounds"] is not None and st["rounds"] <= cambc_env.EARLY_ROUNDS and win:
                early["candidates" if win < 0 else "opponents"] += 1
            us = "teamA" if side == 0 else "teamB"
            for team, c in st["capped"].items():
                capped["candidates" if team == us else "opponents"] += c
            res[name].append((sc, win, gi))
        if not os.environ.get("TUNE_KEEP"):
            shutil.rmtree(self.work, ignore_errors=True)
        for h in self.hashes:
            patch.forget(h)
        if failed:
            log(self.run, f"{self.tag}: {failed} of {len(stems)} games failed")
        if banner := cambc_env.handoff_banner(early, {k: k for k in early}):
            log(self.run, f"{self.tag}: {banner}")
        if any(capped.values()):
            log(self.run, f"{self.tag}: capped drafts (DRAFT-CAPPED): candidates {capped['candidates']} games, "
                          f"opponents {capped['opponents']}")
        return res


def play(run, cfg, cands, games, tag):
    b = Batch(run, cfg, cands, games, tag).start()
    b.wait()
    return b.finish(), b.wall


_MAPS = {}


def draw_games(cfg, rng, n_maps):
    key = tuple(cfg["pool"])
    if key not in _MAPS:
        _MAPS[key] = maps_in(cfg["pool"])
    maps = _MAPS[key]
    return [(m, opp, rng.randrange(2)) for m in rng.sample(maps, n_maps) for opp in cfg["opps"]]


def plan(cfg, k, x):
    """Iteration k's sign vectors, perturbation size, candidates and games, from x."""
    rng = random.Random(cfg["seed"] * 1000003 + k)
    ck = cfg["c"] / (k + 1) ** cfg["gamma"]
    names = list(cfg["params"])
    # An int moves at least 1 each way, or rounding would often play the same value on both sides.
    cn = {n: max(ck, 1.0 / max(1, hi - lo)) if kind == "int" else ck for n, (lo, hi, kind) in cfg["params"].items()}
    # Config `c_min` {name: floor}: an on/off gate keeps a perturbation wide enough to cross its threshold as c_k decays.
    cn = {n: max(v, cfg.get("c_min", {}).get(n, 0.0)) for n, v in cn.items()}
    deltas = [{n: rng.choice((-1, 1)) for n in names} for _ in range(cfg["pairs"])]
    cands = {}
    for p, d in enumerate(deltas):
        cands[f"p{p}"] = values_of(cfg, {n: x[n] + cn[n] * d[n] for n in names})
        cands[f"m{p}"] = values_of(cfg, {n: x[n] - cn[n] * d[n] for n in names})
    return deltas, cn, cands, draw_games(cfg, rng, cfg["maps_per_iter"])


def cmd_run(a):
    """Pipelined: config `inflight` (default 2) iterations play at once, each planned from x as updated by those
    already scored, so one batch's tail overlaps the next and scoring never idles the cores: SPSA with an update
    delay of inflight - 1."""
    from collections import deque
    cambc_env.check_local_header()
    run = RUNS / a.run
    deadline = time.time() + a.hours * 3600 if a.hours else None
    done = 0
    base = patch.Base(run / "base")
    inflight = deque()  # (k, deltas, ck, batch)
    issued = json.loads((run / "state.json").read_text())["k"]
    while True:
        cfg = json.loads((run / "config.json").read_text())  # re-read: editable while running
        while True:
            stop = ((a.iters and done + len(inflight) >= a.iters) or (deadline and time.time() > deadline)
                    or (run / "STOP").exists())
            if stop or len(inflight) >= cfg.get("inflight", 2):
                break
            x = json.loads((run / "state.json").read_text())["x"]
            for n in cfg["params"]:
                x.setdefault(n, 0.5)
            deltas, ck, cands, games = plan(cfg, issued, x)
            inflight.append((issued, deltas, ck, Batch(run, cfg, cands, games, f"it{issued}", base).start()))
            issued += 1
        if not inflight:
            break
        k, deltas, ck, batch = inflight.popleft()
        batch.wait()
        res = batch.finish()
        x = json.loads((run / "state.json").read_text())["x"]
        names = list(cfg["params"])
        # Per-game log for map-conditioned analysis (research/ideas-2026-11-05/mapcond.md). Δ and c_k are logged
        # because a mid-run config edit would break replaying plan() from the seed.
        rec_g = {"k": k + 1, "names": names, "deltas": [[d.get(n, 0) for n in names] for d in deltas],
                 "cn": [ck.get(n) for n in names],
                 "games": [[os.path.relpath(m, ROOT), o, s] for m, o, s in batch.games],
                 "scores": {c: [None] * len(batch.games) for c in res}}
        for c, r in res.items():
            for sc, _, gi in r:
                rec_g["scores"][c][gi] = round(sc, 5)
        with (run / "games.jsonl").open("a") as f:
            f.write(json.dumps(rec_g) + "\n")
        for n in names:
            x.setdefault(n, 0.5)
        ak =cfg["a"] / (k + 1 + cfg["A"]) ** cfg["alpha"]
        mean = {c: (sum(s for s, _, _ in r) / len(r) if r else 0.0) for c, r in res.items()}
        winp = {c: (sum(w > 0 for _, w, _ in r) / len(r) if r else 0.0) for c, r in res.items()}
        grad = {n: 0.0 for n in names}
        for p, d in enumerate(deltas):
            # Paired on the games both played.
            gp = {gi: s for s, _, gi in res[f"p{p}"]}
            gm = {gi: s for s, _, gi in res[f"m{p}"]}
            both = [gi for gi in gp if gi in gm]
            diff = sum(gp[g] - gm[g] for g in both) / len(both) if both else 0.0
            for n in names:
                if n in d:
                    grad[n] += diff / (2 * ck.get(n, cfg["c"]) * d[n]) / len(deltas)
        x = {n: min(1.0, max(0.0, x[n] + ak * grad[n])) for n in names}
        n_games = sum(len(r) for r in res.values())
        rec = {"k": k + 1, "time": time.strftime("%Y-%m-%d %H:%M:%S"), "games": n_games, "wall": round(batch.wall, 1),
               "ak": ak, "ck": min(ck.values()), "mean": mean, "win": winp, "x": x}
        with (run / "history.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        (run / "state.json").write_text(json.dumps({"k": k + 1, "x": x}, indent=1))
        avg = sum(mean.values()) / len(mean)
        log(run, f"it {k + 1}: {n_games} games in {batch.wall:.0f}s ({n_games / max(batch.wall, 1e-9):.0f}/s), mean score "
                 f"{avg:+.4f}, win {100 * sum(winp.values()) / len(winp):.1f}%, step {ak:.4f} c {min(ck.values()):.4f}")
        done += 1


def cmd_status(a):
    run = RUNS / a.run
    cfg = json.loads((run / "config.json").read_text())
    st = json.loads((run / "state.json").read_text())
    base = patch.Base(run / "base")
    d = base.defaults()
    v = values_of(cfg, st["x"])
    print(f"{run}: iteration {st['k']}")
    for n, (lo, hi, kind) in cfg["params"].items():
        mark = "" if abs(v[n] - d[n]) < 0.05 * (hi - lo) else "  *"
        print(f"  {n:32s} {d[n]:>8.3f} -> {v[n]:>8.3f}   [{lo}, {hi}]{mark}")
    hist = [json.loads(l) for l in (run / "history.jsonl").read_text().splitlines()] if (run / "history.jsonl").exists() else []
    for h in hist[-10:]:
        m = h["mean"]
        print(f"  it {h['k']}: {h['games']} games {h['wall']}s, mean {sum(m.values()) / len(m):+.4f}, "
              f"win {100 * sum(h['win'].values()) / len(h['win']):.1f}%")


def cmd_apply(a):
    """Writes the values into a copy's tune.h defaults (the block's initializer) and tune.json."""
    run = RUNS / a.run
    cfg = json.loads((run / "config.json").read_text())
    st = json.loads((run / "state.json").read_text()) if not a.values else {"x": None}
    vals = json.loads(Path(a.values).read_text()) if a.values else values_of(cfg, st["x"])
    out = ROOT / a.out
    copy_bot(run / "base", out)
    spec = json.loads((out / "src" / "tune.json").read_text())
    spec["floats"] = [[n, float(vals.get(n, d))] for n, d in spec["floats"]]
    spec["ints"] = [[n, int(round(vals.get(n, d)))] for n, d in spec["ints"]]
    (out / "src" / "tune.json").write_text(json.dumps(spec, indent=1))
    h = (out / "src" / "tune.h").read_text()
    fv = ", ".join(f"{v!r}f" if "." in repr(v) or "e" in repr(v) else f"{v}.0f" for _, v in spec["floats"])
    iv = ", ".join(str(v) for _, v in spec["ints"])
    h = re.sub(r'= \{"([^"]+)", \{[^}]*\}, \{[^}]*\}\};', lambda m: f'= {{"{m.group(1)}", {{{fv}}}, {{{iv}}}}};', h)
    (out / "src" / "tune.h").write_text(h)
    print(f"{out}: {len(spec['floats'])} floats, {len(spec['ints'])} ints written")


def cmd_play(a):
    run = RUNS / a.run
    cfg = json.loads((run / "config.json").read_text())
    st = json.loads((run / "state.json").read_text())
    vals = json.loads(Path(a.values).read_text()) if a.values else values_of(cfg, st["x"])
    base = patch.Base(run / "base")
    rng = random.Random(a.seed)
    if a.pool:
        cfg = dict(cfg, pool=a.pool.split(","))
    games = draw_games(cfg, rng, max(1, a.games // len(cfg["opps"])))
    res, wall = play(run, cfg, {"cur": vals, "def": base.defaults()}, games, f"play{a.seed}")
    for c, r in res.items():
        print(f"{c}: {len(r)} games, mean score {sum(s for s, _, _ in r) / max(1, len(r)):+.4f}, "
              f"win {100 * sum(w > 0 for _, w, _ in r) / max(1, len(r)):.1f}% ({wall:.0f}s)")
    # Paired by game: the current values' edge over the defaults, with a normal 95% interval.
    cur = {gi: s for s, _, gi in res["cur"]}
    d = [cur[gi] - s for s, _, gi in res["def"] if gi in cur]
    if len(d) > 1:
        m = sum(d) / len(d)
        sd = (sum((x - m) ** 2 for x in d) / (len(d) - 1)) ** 0.5
        print(f"cur - def: {m:+.4f} +- {1.96 * sd / len(d) ** 0.5:.4f} over {len(d)} paired games")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--run", required=True)
    i.add_argument("--bot", required=True)
    i.add_argument("--opps", required=True, help="comma-separated bots under bots/")
    i.add_argument("--pool", help="comma-separated map directories (default: ladder, gen, gen-s1, fresh-92001..92100)")
    i.add_argument("--params", help="comma-separated names (default: every tunified constant)")
    i.add_argument("--maps", type=int, default=64, help="maps an iteration (each against every opponent)")
    i.add_argument("--pairs", type=int, default=4)
    i.add_argument("--seed", type=int, default=1)
    i.add_argument("--force", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--run", required=True)
    r.add_argument("--hours", type=float)
    r.add_argument("--iters", type=int)
    for name in ("status", "apply", "play"):
        s = sub.add_parser(name)
        s.add_argument("--run", required=True)
        if name in ("apply", "play"):
            s.add_argument("--values", help="a JSON file of name -> value (default: the run's current values)")
        if name == "apply":
            s.add_argument("--out", required=True)
        if name == "play":
            s.add_argument("--games", type=int, default=2000)
            s.add_argument("--seed", type=int, default=0)
            s.add_argument("--pool", help="comma-separated map directories instead of the run's pool (held-out maps)")
    a = ap.parse_args()
    {"init": cmd_init, "run": cmd_run, "status": cmd_status, "apply": cmd_apply, "play": cmd_play}[a.cmd](a)


if __name__ == "__main__":
    main()
