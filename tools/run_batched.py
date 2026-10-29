"""Run every map twice, swapping teams (or once, with --one-side). Requires Python 3.10+ and cambc.

Each bot is copied to replays/frozen/ and built there with `cambc build`, then each match runs in its
own `cambc run-batch` while it holds a CPU slot, so concurrent batches share the machine game by game;
separate concurrent `cambc run` calls race on the bots' build caches on Windows."""

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
ERROR_LOG = re.compile(r"\(log: (.+?)\)")


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


def build_bots(cli, bots, env, log, warm_map):
    """Build the bots with `cambc build`, at once (each is one ~25 s single-threaded compile), then
    compile each into the wasmtime cache (cambc_env.warm); write the output to `log` and return the
    first bot that fails, or None. run-batch's own compiles fail on Windows ("unable to open output
    file"), so it must find nothing left to build. Concurrent builds of one bot fail too, hence the lock."""
    def build(bot):
        clear_copied_cache(bot)
        print(f"Building {bot.name}...", flush=True)
        with cpu_slots.exclusive(bot.parent / "build.lock"):
            built = subprocess.run([cli, "build", str(bot)], cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            if not built.returncode and not cambc_env.warm(cli, bot, warm_map):
                built.stdout += f"Warming {bot.name}'s compile cache failed; its first matches compile it\n"
        return built

    unique = list(dict.fromkeys(bots))
    with ThreadPoolExecutor(len(unique)) as pool:
        results = list(pool.map(build, unique))
    with log.open("w", encoding="utf-8") as stream:
        for built in results:
            stream.write(built.stdout)
    return next((bot for bot, built in zip(unique, results) if built.returncode), None)


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
    parser.add_argument("--fuel", type=positive_int, help="Fuel per turn (run-batch --fuel-quantum)")
    parser.add_argument("--timeout", type=positive_int, metavar="SECONDS",
                        help="Wall-clock limit per match; a match over it counts as an error")
    parser.add_argument("--no-replays", action="store_true", help="Keep logs/results only")
    parser.add_argument("--one-side", action="store_true",
                        help="Play each map once, with sides drawn at random (seeded by --side-seed)")
    parser.add_argument("--side-seed", type=nonnegative_int, default=0,
                        help="Seed for --one-side team assignment (default: 0)")
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
        cli = shutil.which("cambc")
        if cli is None:
            raise ValueError("cambc is not on PATH. Install it with: python -m pip install cambc")
        output = (args.output or ROOT / "replays" / datetime.now().strftime("batch-%Y%m%d-%H%M%S-%f")).resolve()
        played = [freeze(bot) for bot in bots]
        for path in (*played, *maps, output):
            manifest_path(path)
        output.mkdir(parents=True, exist_ok=False)
    except (ValueError, OSError) as error:
        parser.error(str(error))

    if args.one_side:
        # More maps for the same games; each side's advantage evens out over the draw.
        sides = random.Random(args.side_seed)
        pairs = [(path, sides.choice(((0, 1), (1, 0)))) for path in maps]
    else:
        pairs = [(path, order) for path in maps for order in ((0, 1), (1, 0))]
    jobs = [(i, path, order) for i, (path, order) in enumerate(pairs)]
    # Start the slowest first so no long game is left running alone at the end.
    # Unknown maps count as slow.
    durations = load_durations()
    jobs.sort(key=lambda job: durations.get(map_key(job[1]), float("inf")), reverse=True)
    stems = {f"{i + 1:03d}-{path.stem}-{'12' if order == (0, 1) else '21'}": (i, path, order)
             for i, path, order in jobs}
    # Replay paths are relative to the manifest's directory, and per-game manifests live in jobs/.
    lines = {stem: f"{manifest_path(played[order[0]])} {manifest_path(played[order[1]])} {manifest_path(path)} "
                   f"{manifest_path(output)}/{stem}.repl26a\n"
             for stem, (i, path, order) in stems.items()}
    manifest = output / "manifest.txt"
    manifest.write_text("".join(lines.values()), encoding="utf-8")
    workers = min(args.threads, len(jobs))
    print(f"Running {len(jobs)} matches on {len(maps)} maps; up to {workers} at once, as CPU slots allow")
    print(f"Bot 1: {bots[0]}\n  as {played[0]}\nBot 2: {bots[1]}\n  as {played[1]}\nResults: {output}", flush=True)
    records = []
    wins = [0, 0]
    errors = 0
    lock = threading.Lock()
    # In a terminal, one progress bar updated in place; in a file, a line per match.
    live = sys.stdout.isatty()

    def record(result):
        nonlocal errors
        with lock:
            records.append(result)
            if "error" in result:
                errors += 1
                outcome = f"ERROR: {result['error']}"
            else:
                wins[result["winner"]] += 1
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
            report = {"bots": [str(p) for p in bots], "fuel": args.fuel, "timeout": args.timeout,
                      "gen": args.gen, "gen_seed": args.gen_seed if args.gen else None,
                      "one_side": args.one_side, "side_seed": args.side_seed if args.one_side else None,
                      "scheduled": len(jobs), "completed": len(records), "wins": wins,
                      "errors": errors, "matches": sorted(records, key=lambda r: r["index"])}
            (output / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    options = ["--color", "never"]
    if args.fuel is not None:
        options += ["--fuel-quantum", str(args.fuel)]
    if args.timeout is not None:
        options += ["--timeout", str(args.timeout)]
    env = cambc_env.env()
    log = output / "run.log"
    started = perf_counter()
    finished = set()

    def finish(stem, team, failure, rounds, seconds):
        index, path, order = stems[stem]
        replay = output / f"{stem}.repl26a"
        result = {"index": index, "map": str(path), "order": list(order),
                  "replay": str(replay) if replay.is_file() and not args.no_replays else None}
        if failure is not None:
            error_log = ERROR_LOG.search(failure)
            result["error"] = ERROR_LOG.sub("", failure).strip() + (
                f". See {Path(error_log.group(1)).name}" if error_log else "")
        else:
            result.update(winner=order[team == "B"], rounds=int(rounds))
        if args.no_replays:
            replay.unlink(missing_ok=True)
        result["seconds"] = round(seconds, 3)
        finished.add(stem)
        record(result)

    def run(batch, manifest, held, stream):
        """Play `batch` (stems, all in `manifest`) in one run-batch, a match per held slot; free the slots at its end."""
        began = perf_counter()
        match_started = {}
        pending = set(batch)
        status = None
        try:
            with subprocess.Popen(
                [cli, "run-batch", str(manifest), "--jobs", str(len(held)), *options], cwd=output, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                bufsize=1,
            ) as proc:
                for raw in proc.stdout:
                    with lock:
                        stream.write(raw)
                        stream.flush()
                    line = ANSI.sub("", raw.rstrip("\r\n"))
                    if found := STATUS.match(line):
                        status = found
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
                    finish(stem, team, failure, rounds, perf_counter() - match_started.get(stem, began))
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

    failed_build = build_bots(cli, played, env, log, maps[0])
    if failed_build is None:
        if live:
            redraw(progress(0, len(jobs), wins, errors))
        with log.open("a", encoding="utf-8") as stream:
            if PER_GAME:
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
                # Slowest first. One slot poller per batch: a slot freed anywhere goes to whichever batch polls next.
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
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
