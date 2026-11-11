"""Run every map twice, swapping teams (or once, with --one-side). Requires Python 3.10+ and cambc.

Each bot is copied to replays/frozen/ and built there with `cambc build`, then each match runs in its
own `cambc run-batch` while it holds a CPU slot, so concurrent batches share the machine game by game;
separate concurrent `cambc run` calls race on the bots' build caches on Windows. With CAMBC_BIN set to
tools/fastengine/runner/fastrunner, the whole batch goes to one fastrunner run-batch, which takes a slot per game."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import threading
from time import perf_counter, sleep

import cambc_env
import cpu_slots
import experiment_config

sys.path.insert(0, str(Path(__file__).resolve().parent / "fuel"))
import oof  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
GEN_DIR = ROOT / "maps" / "gen"
FROZEN = ROOT / "replays" / "frozen"
# Top-level entries of a bot directory that are build output, not source.
BUILD_OUTPUT = {".cambc", "build", "target", ".cache", "compile_commands.json"}
# Each match in its own run-batch, holding a CPU slot only while it plays. Not on Windows: there every
# run-batch reconfigures both bots' CMake builds as it starts, and concurrent ones break each other's, so
# a Windows batch is one run-batch that keeps the slots free at its start.
PER_GAME = sys.platform != "win32"
# Last seen seconds per map, used only to start the slowest games first.
DURATIONS = ROOT / "replays" / "durations.json"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
# run-batch prints a status line per event, then "    Replay: PATH" naming the match.
# A full tie goes to team B, so there are no draws.
STATUS = re.compile(r"^\[.\] (STARTING|TEAM ([AB]) WIN \(.*?\)|FAILED: (.*?))  .*?(?:Round (\d+)/\d+)?\s*$")
REPLAY = re.compile(r"^\s+Replay: (.+?)\s*$")
# The fast runner's exact out-of-fuel play turns per team (between a win line and its Replay line; not stock's).
OOF_LINE = re.compile(r"^\s+Out of fuel: A (\d+) B (\d+)\s*$")
ERROR_LOG = re.compile(r"\(log: (.+?)\)")
# CAMBC_BIN names a drop-in replacement for cambc used for every cambc call here, e.g. the fast runner
# (tools/fastengine/runner/fastrunner). Unset: the cambc on PATH.
CAMBC_BIN = os.environ.get("CAMBC_BIN")
# A local oarena (gitignored .oarena/) records these games: each bot's bundle and each game's summary are kept
# for it. Without one, nothing changes.
LOCAL_ARENA = (ROOT / ".oarena").is_dir()


def positive_int(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def nonnegative_int(value):
    value = int(value)
    if value < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
    return value


def find_maps(maps_dir, gen=None, gen_seed=0):
    """Maps under maps_dir (skipping the map sets in subdirectories of maps/ below it, so maps/ alone
    is the ladder), or with --gen all generated maps in maps/gen (gen=0) or a seeded sample of gen of them."""
    if gen is not None:
        pool = sorted(p.resolve() for p in GEN_DIR.glob("*.map26a"))
        if not pool:
            raise ValueError(f"No generated maps in {GEN_DIR}; run: node tools/mapgen/mapgen.mjs suite")
        if gen > len(pool):
            raise ValueError(f"--gen {gen} exceeds the {len(pool)} generated maps in {GEN_DIR}")
        return sorted(random.Random(gen_seed).sample(pool, gen)) if gen else pool
    maps_dir = maps_dir.resolve()
    skip = {d.resolve() for d in (ROOT / "maps").iterdir() if d.is_dir() and maps_dir in d.resolve().parents}
    found = []
    for base, dirs, files in os.walk(maps_dir):
        dirs[:] = [d for d in dirs if (Path(base) / d).resolve() not in skip]
        found += [(Path(base) / f).resolve() for f in files if f.endswith(".map26a")]
    return sorted(found)


def map_key(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_durations():
    try:
        return json.loads(DURATIONS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_durations(records):
    """Merge this batch's slowest game per map into the cache; other maps keep their entries."""
    durations = load_durations()
    batch = {}
    for r in records:
        if "error" not in r:
            key = map_key(Path(r["map"]))
            batch[key] = max(batch.get(key, 0), r["seconds"])
    durations.update(batch)
    try:
        DURATIONS.parent.mkdir(parents=True, exist_ok=True)
        DURATIONS.write_text(json.dumps(durations, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass


def bot_path(value):
    for path in (Path(value), ROOT / "bots" / value):
        if path.is_dir():
            return path.resolve()
    raise ValueError(f"Bot not found: {value}")


def manifest_path(path):
    """The manifest is whitespace-separated, so its paths cannot contain spaces."""
    text = path.as_posix()
    if any(c.isspace() for c in text):
        raise ValueError(f"Path contains whitespace, which run-batch manifests cannot hold: {text}")
    return text


def is_fastrunner(cli):
    """Whether cli is tools/fastengine/runner's fastrunner, which plays a whole batch in one run-batch and takes
    a CPU slot per game itself (--slot-dir), so concurrent batches still share the slots game by game."""
    try:
        probe = subprocess.run([cli, "__fastrunner"], cwd=ROOT, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0 and probe.stdout.startswith("fastrunner")


# The launcher runs stock cambc under a cambc build it was not ported to (or with its library unbuilt): games stay
# right but run ~4.7x slower, and release builds report no out-of-fuel counts (14:44-15:19 on 2026-11-09).
FASTRUNNER_DOWN = ("{cli} is the fast runner, but `{cli} __fastrunner` does not answer, so stock cambc would play every "
                   "game: the installed cambc is not the build it was ported to (research/fastengine/RUNNER.md), or "
                   "its library is not built. Port or rebuild it, or set FASTRUNNER_ALLOW_STOCK=1 to play stock")


def fastrunner_unanswered(cli):
    """Whether cli is a fast runner launcher that would fall back to stock (FASTRUNNER_ALLOW_STOCK=1 allows it)."""
    return Path(cli).name == "fastrunner" and not os.environ.get("FASTRUNNER_ALLOW_STOCK") and not is_fastrunner(cli)


def columns():
    return shutil.get_terminal_size().columns


def progress(done, total, wins, errors):
    """One status line from bot 1's side: [####------]  37/80  W 21  L 16  (57%).
    The bar narrows to fit the terminal."""
    rate = f"{100 * wins[0] / (done - errors):.0f}%" if done > errors else "-"
    tail = f" {done:3}/{total}  W {wins[0]}  L {wins[1]}  ({rate})" + (f"  E {errors}" if errors else "")
    width = max(5, min(30, columns() - 3 - len(tail)))
    filled = width * done // total if total else 0
    return f"[{'#' * filled}{'-' * (width - filled)}]{tail}"


def redraw(line):
    """Rewrite the terminal's current line in place. A line reaching the last
    column wraps, and \\r then only returns to the wrapped part, so cut it short."""
    print(f"\r{line[:columns() - 1]}\x1b[K", end="", flush=True)


def newest_batch():
    batches = [p for p in (ROOT / "replays").glob("batch-*") if p.is_dir()]
    return max(batches, key=lambda p: p.stat().st_mtime, default=None)


def watch(target):
    """Follow a batch's results.json (default: the newest batch, then any newer one) until Ctrl+C."""
    shown = None
    try:
        while True:
            batch = target or newest_batch()
            if batch is None:
                redraw("Waiting for a batch under replays/...")
            else:
                try:
                    report = json.loads((batch / "results.json").read_text(encoding="utf-8"))
                except FileNotFoundError:
                    report = None
                except (OSError, ValueError):
                    report = False  # Mid-write: keep the last line.
                if report is not False:
                    if batch != shown and report:
                        print(("\n" if shown else "") + f"\r\x1b[K{batch.name}: "
                              f"{Path(report['bots'][0]).name} vs {Path(report['bots'][1]).name}")
                        shown = batch
                    if report:
                        redraw(progress(report["completed"], report["scheduled"], report["wins"],
                                        report["errors"]))
                        if target and report["completed"] == report["scheduled"]:
                            print()
                            return 0
                    elif batch != shown:
                        redraw(f"{batch.name}: building both bots...")
            sleep(1)
    except KeyboardInterrupt:
        print()
        return 0


def clear_copied_cache(bot):
    """A bot copied with its .cambc/build keeps a CMake cache pointing at the original's build
    directory, and every build of the copy then fails; delete such a cache."""
    build = bot / ".cambc" / "build"
    cache = build / "CMakeCache.txt"
    if not cache.is_file():
        return
    for line in cache.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("bot_BINARY_DIR:"):
            recorded = Path(line.split("=", 1)[1])
            if recorded.resolve() != build.resolve():
                print(f"Clearing {bot.name}'s build cache copied from {recorded}", flush=True)
                shutil.rmtree(build)
            return


def freeze(bot):
    """A copy of the bot's source at replays/frozen/<hash of it and the SDK>/<name>. Every match of a
    batch starts its own run-batch, which rebuilds a bot whose source changed, so playing the copy keeps
    the whole batch on the source it started with; batches of the same source share the copy's build."""
    digest = hashlib.sha256()
    for base in (bot, ROOT / "sdk" / "cpp"):
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(base)
            if path.is_file() and not (base == bot and rel.parts[0] in BUILD_OUTPUT):
                digest.update(rel.as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    copy = FROZEN / digest.hexdigest()[:12] / bot.name
    if not copy.is_dir():
        copy.parent.mkdir(parents=True, exist_ok=True)
        staging = copy.parent / f".{bot.name}-{os.getpid()}"
        shutil.copytree(bot, staging, ignore=lambda d, names: BUILD_OUTPUT & set(names) if Path(d) == bot else ())
        try:
            staging.rename(copy)
        except OSError:  # Another batch froze the same source first.
            shutil.rmtree(staging, ignore_errors=True)
    return copy


def build_bots(cli, bots, env, log, warm_map, release=False, configured_ref=False):
    """Build the bots with `cambc build`, at once (each is one ~25 s single-threaded compile), then
    compile each into the wasmtime cache (cambc_env.warm); write the output to `log` and return the
    first bot that fails, or None. run-batch's own compiles fail on Windows ("unable to open output
    file"), so it must find nothing left to build. Concurrent builds of one bot fail too, hence the lock."""
    def build(bot):
        clear_copied_cache(bot)
        print(f"Building {bot.name}...", flush=True)
        with cpu_slots.exclusive(bot.parent / "build.lock"):
            built = subprocess.run([cli, "build", str(bot), *(["--release"] if release else [])], cwd=ROOT, env=({**env, "CMAKE_BUILD_PARALLEL_LEVEL": "1"} if configured_ref else env),
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                   errors="replace")
            if not built.returncode and not configured_ref and not cambc_env.warm(cli, bot, warm_map, ["--release"] if release else []):
                built.stdout += f"Warming {bot.name}'s compile cache failed; its first matches compile it\n"
        return built

    unique = list(dict.fromkeys(bots))
    # cpu_slots membership is process-global: reserve once outside the build threads.
    reservation = cpu_slots.acquire(len(unique), least=1) if configured_ref else []
    try:
        with ThreadPoolExecutor(len(reservation) if configured_ref else len(unique)) as pool:
            results = list(pool.map(build, unique))
    finally:
        cpu_slots.release(reservation)
    with log.open("w", encoding="utf-8") as stream:
        for built in results:
            stream.write(built.stdout)
    return next((bot for bot, built in zip(unique, results) if built.returncode), None)


def prepare_experiment_cache(cli, manifest, options, env, log):
    """Compile the manifest's bot/metering entries into the native cache, holding up to the compiler's 16 slots;
    dispatch no games."""
    env['FASTRUNNER_BUILT'] = '1'
    # Whatever fair share grants: on a shared pool a group's share can stay under 16, and a wait for all 16 never ends.
    held = cpu_slots.acquire(16, least=1)
    try:
        with log.open('a') as stream:
            prepared = subprocess.run([cli, 'run-batch', str(manifest), '--prepare-only', *options],
                                      cwd=manifest.parent, env=env, stdout=stream, stderr=subprocess.STDOUT)
        if prepared.returncode:
            raise RuntimeError('Runtime opponent cache preparation failed; no matches dispatched')
    finally:
        cpu_slots.release(held)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bot1", nargs="?", help="Bot name under bots/, or a path")
    parser.add_argument("bot2", nargs="?", help="Bot name under bots/, or a path")
    parser.add_argument("--watch", nargs="?", const="", metavar="DIR",
                        help="Instead, show a live progress bar for batch DIR, or else the newest batch "
                        "under replays/ and each newer one")
    parser.add_argument("--threads", type=positive_int, default=cpu_slots.SIZE,
                        help=f"Most concurrent matches, as CPU slots allow (default: all {cpu_slots.SIZE})")
    parser.add_argument("--maps-dir", type=Path,
                        help="Recursively find all .map26a files here (default: maps/ without its subdirectories, the ladder)")
    parser.add_argument("--gen", nargs="?", type=nonnegative_int, const=0, metavar="N",
                        help="Instead, play the generated maps in maps/gen (node tools/mapgen/mapgen.mjs suite): "
                        "all of them, or N sampled by --gen-seed")
    parser.add_argument("--gen-seed", type=nonnegative_int, default=0, help="Seed for choosing --gen N maps (default: 0)")
    parser.add_argument("--output", type=Path, help="New results directory (default: replays/batch-TIMESTAMP)")
    parser.add_argument("--game-timeout", type=float, help="Opt-in native per-game wallclock limit; no timed-out game retry")
    parser.add_argument("--experiment-config", type=Path, help="Per-map native REF runtime config JSON; explicit experimental opponents only")
    parser.add_argument("--fuel", type=positive_int, help="Fuel per turn (run-batch --fuel-quantum)")
    parser.add_argument("--timeout", type=positive_int, metavar="SECONDS",
                        help="Wall-clock limit per match; a match over it counts as an error")
    parser.add_argument("--no-replays", action="store_true", help="Keep logs/results only")
    parser.add_argument("--release", action="store_true",
                        help="Build and play release builds, as the platform does: debug_block is compiled out, so "
                        "games differ from debug builds' and cost ~15%% less CPU. Bots print no OOF lines; the fast "
                        "runner's own counts go to each match's oof_turns (stock cambc gives none)")
    parser.add_argument("--keep-replays", type=positive_int, metavar="N",
                        help="Keep only the first N finished games' replays (failed games' are always kept); each later "
                        "one is deleted once its out-of-fuel and handoff lines are saved to pruned-stdout.jsonl "
                        "(tools/fuel/oof.py reads them) and its match lists it as \"pruned\" (default: keep all)")
    parser.add_argument("--one-side", action="store_true",
                        help="Play each map once, with sides drawn at random (seeded by --side-seed)")
    parser.add_argument("--side-seed", type=nonnegative_int, default=0,
                        help="Seed for --one-side team assignment (default: 0)")
    parser.add_argument("--shuffle", type=nonnegative_int, metavar="SEED",
                        help="Play the maps in a random order seeded by SEED, each map's two sides together, instead "
                        "of slowest first, so any prefix of the batch is a fair sample (ab.py --sprt)")
    args = parser.parse_args()
    if args.watch is not None:
        return watch(Path(args.watch).resolve() if args.watch else None)
    if args.bot1 is None or args.bot2 is None:
        parser.error("bot1 and bot2 are required")
    if args.gen is not None and args.maps_dir is not None:
        parser.error("--gen and --maps-dir cannot be combined")
    try:
        bots = [bot_path(args.bot1), bot_path(args.bot2)]
        maps = find_maps(args.maps_dir or ROOT / "maps", args.gen, args.gen_seed)
        if not maps:
            raise ValueError(f"No .map26a files found in {args.maps_dir or ROOT / 'maps'}")
        # Absolute: games run with cwd=ROOT.
        cli = str(Path(CAMBC_BIN).resolve()) if CAMBC_BIN else shutil.which("cambc")
        if cli is None:
            raise ValueError("cambc is not on PATH. Install it with: python -m pip install cambc")
        if CAMBC_BIN and not Path(cli).is_file():
            raise ValueError(f"CAMBC_BIN={CAMBC_BIN} does not exist")
        if CAMBC_BIN and fastrunner_unanswered(cli):
            raise ValueError(FASTRUNNER_DOWN.format(cli=cli))
        config, config_proof = experiment_config.load(args.experiment_config, maps)
        if args.game_timeout is not None and (not 0 < args.game_timeout <= 86400 or not is_fastrunner(cli)):
            raise ValueError('game timeout requires fast runner and (0,86400] seconds')
        if config is not None and (not is_fastrunner(cli) or os.environ.get('FASTRUNNER_MODE') != 'native'):
            raise ValueError('experiment configuration requires the native fast runner')
        output = (args.output or ROOT / "replays" / datetime.now().strftime("batch-%Y%m%d-%H%M%S-%f")).resolve()
        played = [freeze(bot) for bot in bots]
        for path in (*played, *maps, output):
            manifest_path(path)
        output.mkdir(parents=True, exist_ok=False)
        if LOCAL_ARENA and not args.no_replays:
            (output / "bundles").mkdir()
            for i, bot in enumerate(played):
                subprocess.run([cli, "bundle", str(bot), "--output", str(output / "bundles" / f"bot{i + 1}.zip")],
                               cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (ValueError, OSError) as error:
        parser.error(str(error))

    if args.one_side:
        # More maps for the same games; each side's advantage evens out over the draw.
        sides = random.Random(args.side_seed)
        pairs = [(path, sides.choice(((0, 1), (1, 0)))) for path in maps]
    else:
        pairs = [(path, order) for path in maps for order in ((0, 1), (1, 0))]
    jobs = [(i, path, order) for i, (path, order) in enumerate(pairs)]
    if args.shuffle is not None:
        # Every runner plays the manifest in order, so this is the play order.
        rank = {path: k for k, path in enumerate(random.Random(args.shuffle).sample(maps, len(maps)))}
        jobs.sort(key=lambda job: (rank[job[1]], job[0]))
    else:
        # Start the slowest first so no long game is left running alone at the end.
        # Unknown maps count as slow.
        durations = load_durations()
        jobs.sort(key=lambda job: durations.get(map_key(job[1]), float("inf")), reverse=True)
    stems = {f"{i + 1:03d}-{path.stem}-{'12' if order == (0, 1) else '21'}": (i, path, order)
             for i, path, order in jobs}
    # Replay paths are relative to the manifest's directory, and per-game manifests live in jobs/.
    lines = {stem: f"{manifest_path(played[order[0]])} {manifest_path(played[order[1]])} {manifest_path(path)} "
                   f"{manifest_path(output)}/{stem}.repl26a"
                   f"{f' --statistics {manifest_path(output)}/{stem}.camstat' if LOCAL_ARENA and not args.no_replays else ''}"
                   f"{experiment_config.suffix(config, path, order)}\n"
             for stem, (i, path, order) in stems.items()}
    manifest = output / "manifest.txt"
    manifest.write_text("".join(lines.values()), encoding="utf-8")
    workers = min(args.threads, len(jobs))
    print(f"Running {len(jobs)} matches on {len(maps)} maps; up to {workers} at once, as CPU slots allow")
    print(f"Bot 1: {bots[0]}\n  as {played[0]}\nBot 2: {bots[1]}\n  as {played[1]}\nResults: {output}", flush=True)
    records = []
    wins = [0, 0]
    early = [0, 0]  # games each bot lost by cambc_env.EARLY_ROUNDS
    errors = 0
    lock = threading.Lock()
    # In a terminal, one progress bar updated in place; in a file, a line per match.
    live = sys.stdout.isatty()

    last_write = [0.0]
    # Replays past --keep-replays, thinned in one group before each results.json write: a group costs one fsync where
    # a replay at a time cost one a game (about 30 games/s a suite). Thinning before the write keeps a written
    # results.json from listing a replay that is then deleted.
    thinning = []

    def thin_pending():
        present = [(result, replay) for result, replay in thinning if replay.exists()]
        thinning.clear()
        if present:
            oof.thin(output, [replay for _, replay in present])
        for result, replay in present:
            if not replay.exists():
                seconds = result.pop("seconds")  # "pruned" keeps its place before "seconds"
                result.update(replay=None, pruned=replay.name, seconds=seconds)

    def write_results():
        thin_pending()
        report = {"bots": [str(p) for p in bots], "experiment_config": config_proof, "game_timeout": args.game_timeout, "fuel": args.fuel, "release": args.release, "timeout": args.timeout,
                  "gen": args.gen, "gen_seed": args.gen_seed if args.gen else None,
                  "one_side": args.one_side, "side_seed": args.side_seed if args.one_side else None,
                  "scheduled": len(jobs), "completed": len(records), "wins": wins, "early_losses": early,
                  "errors": errors, "matches": sorted(records, key=lambda r: r["index"])}
        # Replaced whole, so a reader (ab.py --sprt, --watch) or a kill never sees it half-written.
        staging = output / "results.json.tmp"
        staging.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        for _ in range(50):
            try:
                os.replace(staging, output / "results.json")
                break
            except PermissionError:  # Windows, while a reader has it open.
                sleep(0.02)
        last_write[0] = perf_counter()

    def record(result, prune=None):
        nonlocal errors
        with lock:
            records.append(result)
            if prune is not None:
                thinning.append((result, prune))
            if "error" in result:
                errors += 1
                outcome = f"ERROR: {result['error']}"
            else:
                wins[result["winner"]] += 1
                early[1 - result["winner"]] += result["rounds"] <= cambc_env.EARLY_ROUNDS
                outcome = f"bot {result['winner'] + 1} wins in {result['rounds']} rounds"
            a, b = (i + 1 for i in result["order"])
            line = (f"[{len(records):2}/{len(jobs)}] {Path(result['map']).name} "
                    f"A={a} B={b}: {outcome} ({result['seconds']:.1f}s)")
            if not live:
                print(line, flush=True)
            else:
                if "error" in result:
                    print(f"\r{line}\x1b[K")
                redraw(progress(len(records), len(jobs), wins, errors))
            # Rewriting the whole file every game is quadratic: ~10 games/s at 40k games in one batch.
            if len(records) == len(jobs) or perf_counter() - last_write[0] >= 1.0:
                write_results()

    options = ["--color", "never", *(["--release"] if args.release else [])]
    # Each team's stdout cap (run-batch --log-limit; 1 MiB by default), for heavily traced bots.
    if os.environ.get("CAMBC_LOG_LIMIT"):
        options += ["--log-limit", os.environ["CAMBC_LOG_LIMIT"]]
    if args.game_timeout is not None:
        options += ["--game-timeout", str(args.game_timeout)]
    if args.fuel is not None:
        options += ["--fuel-quantum", str(args.fuel)]
    if args.timeout is not None:
        options += ["--timeout", str(args.timeout)]
    env = cambc_env.env()
    log = output / "run.log"
    started = perf_counter()
    finished = set()
    kept = [0]

    def finish(stem, team, failure, rounds, seconds, oof_turns=None):
        index, path, order = stems[stem]
        replay = output / f"{stem}.repl26a"
        result = {"index": index, "map": str(path), "order": list(order),
                  "replay": str(replay) if replay.is_file() and not args.no_replays else None,
                  "runtime_config": experiment_config.teams(config, path, order)}
        if failure is not None:
            error_log = ERROR_LOG.search(failure)
            result["error"] = ERROR_LOG.sub("", failure).strip() + (
                f". See {Path(error_log.group(1)).name}" if error_log else "")
        else:
            result.update(winner=order[team == "B"], rounds=int(rounds))
            if oof_turns is not None:
                # By bot: order[0] played team A.
                result["oof_turns"] = [oof_turns[order.index(0)], oof_turns[order.index(1)]]
        prune = None
        if args.no_replays:
            replay.unlink(missing_ok=True)
        elif args.keep_replays and result["replay"] and failure is None:
            with lock:
                kept[0] += 1
                if kept[0] > args.keep_replays:
                    prune = replay
        result["seconds"] = round(seconds, 3)
        finished.add(stem)
        record(result, prune)

    def run(batch, manifest, held, stream, jobs=None):
        """Play `batch` (stems, all in `manifest`) in one run-batch, a match per held slot (or with `jobs`, the
        run-batch options that say how many at once); free the slots at its end."""
        began = perf_counter()
        match_started = {}
        pending = set(batch)
        status, oof_turns = None, None
        try:
            with subprocess.Popen(
                [cli, "run-batch", str(manifest), *(jobs or ["--jobs", str(len(held))]), *options], cwd=output, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                bufsize=1,
            ) as proc:
                for raw in proc.stdout:
                    with lock:
                        stream.write(raw)
                        stream.flush()
                    line = ANSI.sub("", raw.rstrip("\r\n"))
                    if found := STATUS.match(line):
                        status, oof_turns = found, None
                        continue
                    if found := OOF_LINE.match(line):
                        oof_turns = [int(found.group(1)), int(found.group(2))]
                        continue
                    found = REPLAY.match(line)
                    if not found or status is None:
                        continue
                    stem = re.split(r"[\\/]", found.group(1))[-1].removesuffix(".repl26a")
                    kind, team, failure, rounds = status.groups()
                    status = None
                    if stem not in pending:
                        continue
                    if kind == "STARTING":
                        match_started[stem] = perf_counter()
                        continue
                    pending.discard(stem)
                    finish(stem, team, failure, rounds, perf_counter() - match_started.get(stem, began), oof_turns)
            code = proc.returncode
        except OSError as error:
            code = error
        finally:
            cpu_slots.release(held)
        # Matches run-batch never reported.
        for stem in sorted(pending):
            index, path, order = stems[stem]
            record({"index": index, "map": str(path), "order": list(order), "replay": None,
                    "error": f"run-batch exit {code}; no result. See run.log", "seconds": 0.0})

    cambc_env.check_local_header()
    failed_build = build_bots(cli, played, env, log, maps[0], args.release, configured_ref=config is not None)
    if not failed_build and config is not None:
        prepare_experiment_cache(cli, manifest, options, env, log)

    if failed_build is None:
        if live:
            redraw(progress(0, len(jobs), wins, errors))
        with log.open("a", encoding="utf-8") as stream:
            if CAMBC_BIN and is_fastrunner(cli):
                run(list(stems), manifest, [], stream,
                    ["--jobs", str(workers), "--slot-dir", str(cpu_slots.DIR), "--slots", str(cpu_slots.SIZE)])
            elif PER_GAME:
                jobs_dir = output / "jobs"
                jobs_dir.mkdir()
                running = threading.BoundedSemaphore(workers)

                def play(stem, held):
                    try:
                        job = jobs_dir / f"{stem}.txt"
                        job.write_text(lines[stem], encoding="utf-8")
                        run([stem], job, held, stream)
                    finally:
                        running.release()

                threads = []
                # In job order. One slot poller per batch: a slot freed anywhere goes to whichever batch polls next.
                for stem in stems:
                    running.acquire()
                    threads.append(threading.Thread(target=play, args=(stem, cpu_slots.acquire(1, poll=0.05))))
                    threads[-1].start()
                for thread in threads:
                    thread.join()
                shutil.rmtree(jobs_dir, ignore_errors=True)
            else:
                run(list(stems), manifest, cpu_slots.acquire(workers, least=min(workers, 4)), stream)
    else:
        for stem, (index, path, order) in stems.items():
            record({"index": index, "map": str(path), "order": list(order), "replay": None,
                    "error": f"{failed_build.name} failed to build. See run.log", "seconds": 0.0})
    with lock:
        write_results()
    save_durations(records)
    if live:
        print()
    if not finished:
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-15:]
        print("No matches ran; end of run.log:\n" + "\n".join(f"  {t}" for t in tail))

    completed = len(records) - errors
    print(f"\nSummary: {completed}/{len(jobs)} successful matches in {perf_counter() - started:.1f}s")
    for i, bot in enumerate(bots):
        rate = 100 * wins[i] / completed if completed else 0
        print(f"  Bot {i + 1} ({bot.name}): {wins[i]} wins ({rate:.1f}% of successful matches)")
    print(f"  Errors: {errors}\n  Results: {output / 'results.json'}")
    if banner := cambc_env.handoff_banner(dict(enumerate(early)), {i: f"bot {i + 1} ({bot.name})" for i, bot in enumerate(bots)}):
        print(banner)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
