"""Full A/B of two bots through run_batched.py: ladder, generated and fresh-seed maps, both sides.

    py tools/ab.py orch/my-branch main --name my-change
    py tools/ab.py astraeus baselines/v66 --no-test-draft
    py tools/ab.py main HEAD~1 --no-test-draft --suites ladder,gen
    py tools/ab.py astraeus variants/astraeus-38aa25c --no-test-draft --sprt --sprt-stop low

CAND and REF are each a git ref (branch, sha, main), whose bots/archives/hyperion (bots/hyperion
before its 2026-11-11 retirement, bots/hecate before the 2026-10-21 rename) is materialised with git archive into bots/variants/ab-<name>-<cand|ref>-<sha7>/
with params::test_draft switched on, or a bot directory under bots/ (astraeus) used as it is. Wins are CAND's.
Suites: ladder (maps/), gen (maps/gen), fresh (every maps/gen-s*/), or any directory of maps.

--sprt plays the maps in a seeded random order and stops every suite once a sequential probability ratio test
decides between H0 (CAND's win rate is P0) and H1 (it is P1), on maps both of whose games have finished, all
suites together: LLR = N (P1 - P0) (2m - P0 - P1) / (2v) over N maps with mean score m and variance v (the
normal approximation fishtest uses), accepting H0 at ln(beta / (1 - alpha)) and H1 at ln((1 - beta) / alpha).
After a stop, the win rates are from a partial sample of each suite."""

import argparse
import collections
import contextlib
from datetime import datetime
import io
import json
import hashlib
import math
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import re
import signal
import subprocess
import sys
import tarfile
from time import monotonic, perf_counter, sleep

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "fuel"))
sys.path.insert(0, str(ROOT / "tools"))
import cambc_env  # noqa: E402
import cpu_slots  # noqa: E402
import oof  # noqa: E402

VARIANTS = ROOT / "bots" / "variants"
TEST_DRAFT = re.compile(r"^(\s*(?:inline\s+)?constexpr\s+bool\s+test_draft\s*=\s*)(false|true)(\s*;)", re.M)


def git(*args, binary=False):
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=not binary)
    return done.stdout if done.returncode == 0 else None


def slug(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "x"


def resolve(spec):
    for path in (ROOT / "bots" / spec, Path(spec)):
        if (path / "src").is_dir():
            return {"spec": spec, "kind": "dir", "path": path.resolve()}
    sha = git("rev-parse", "--verify", "--quiet", f"{spec}^{{commit}}")
    if not sha:
        raise ValueError(f"{spec!r} is neither a bot directory under bots/ nor a git ref")
    return {"spec": spec, "kind": "git", "sha": sha.strip()}


def write_if_changed(path, data):
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def materialise(side, role, name, test_draft):
    """Write the bot at side's commit into a variant directory, rewriting only changed files
    so its build cache stays incremental."""
    sha = side["sha"]
    # Commits before the 2026-11-11 retirement have the bot at bots/hyperion; before the 2026-10-21 rename, bots/hecate.
    for bot in ("bots/archives/hyperion", "bots/hyperion", "bots/hecate"):
        data = git("archive", "--format=tar", f"{sha}:{bot}", binary=True)
        if data:
            break
    else:
        raise ValueError(f"git archive found none of bots/archives/hyperion, bots/hyperion, bots/hecate at {side['spec']} ({sha[:7]})")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            rel = Path(member.name).as_posix()
            if member.isfile() and rel.split("/")[0] != ".cambc":
                files[rel] = tar.extractfile(member).read()
    if test_draft:
        text = files.get("src/params.h", b"").decode("utf-8")
        found = TEST_DRAFT.findall(text)
        if len(found) != 1:
            raise ValueError(f"{bot}/src/params.h at {side['spec']} ({sha[:7]}) needs exactly one "
                             f"'constexpr bool test_draft = false;' line (found {len(found)}); "
                             "pass --no-test-draft to use it unchanged")
        files["src/params.h"] = TEST_DRAFT.sub(r"\1true\3", text).encode("utf-8")
    target = VARIANTS / f"ab-{name}-{role}-{sha[:7]}"
    for rel, blob in files.items():
        write_if_changed(target / rel, blob)
    for path in sorted(target.rglob("*"), reverse=True):
        rel = path.relative_to(target).as_posix()
        if rel.split("/")[0] in (".cambc", "ab.json"):
            continue
        if path.is_file() and rel not in files:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    write_if_changed(target / "ab.json", (json.dumps(
        {"spec": side["spec"], "sha": sha, "test_draft": test_draft}, indent=2) + "\n").encode("utf-8"))
    return target


def suites(tokens):
    """[(label, run_batched args)] plus notes on suites that have no maps."""
    out, notes = [], []
    for token in tokens:
        if token == "ladder":
            out.append(("ladder", []))
        elif token == "gen":
            out.append(("gen", ["--gen"]))
        elif token == "fresh":
            dirs = sorted(d for d in (ROOT / "maps").glob("gen-s*") if d.is_dir())
            out += [(f"fresh/{d.name}", ["--maps-dir", str(d)]) for d in dirs]
            if not dirs:
                notes.append("fresh: no maps/gen-s*/ directories, skipped")
        elif Path(token).is_dir():
            out.append((Path(token).resolve().name, ["--maps-dir", str(Path(token).resolve())]))
        else:
            raise ValueError(f"Unknown suite {token!r}: use ladder, gen, fresh or a directory of maps")
    return out, notes


def wilson(wins, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def rate(wins, n):
    lo, hi = wilson(wins, n)
    pct = f"{100 * wins / n:.1f}%" if n else "-"
    return f"{pct} of {n} ({wins}-{n - wins}), 95% CI {lo:.1f}-{hi:.1f}"


def rel(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def describe(side):
    return f"{side['spec']} ({side['sha'][:7]})" if side["kind"] == "git" else f"{side['spec']} (dir)"


def hypotheses(text):
    try:
        p0, p1 = (float(x) for x in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected P0,P1 (CAND's win rates), such as 0.50,0.52; got {text!r}") from None
    if not 0 < p0 < p1 < 1:
        raise argparse.ArgumentTypeError(f"need 0 < P0 < P1 < 1; got {text!r}")
    return p0, p1


def error_rate(text):
    value = float(text)
    if not 0 < value < 0.5:
        raise argparse.ArgumentTypeError(f"must be between 0 and 0.5; got {text!r}")
    return value


def llr(scores, p0, p1):
    """Log-likelihood ratio of H1 (mean score p1) over H0 (p0) from per-map-pair scores, by the normal approximation."""
    n = len(scores)
    if not n:
        return 0.0
    mean = sum(scores) / n
    # Floored: a run of identical pairs has no variance.
    var = max(sum((x - mean) ** 2 for x in scores) / n, 1e-3)
    return n * (p1 - p0) * (2 * mean - p0 - p1) / (2 * var)


def sprt_bounds(alpha, beta):
    """(accept H0 at or below, accept H1 at or above)."""
    return math.log(beta / (1 - alpha)), math.log((1 - beta) / alpha)


def sprt_state(reports, p0, p1, bounds):
    """The SPRT over every suite's finished matches: a map counts once both its games have finished, scoring CAND's
    mean, since one map's two sides are correlated."""
    sides = collections.defaultdict(dict)
    games = 0
    for label, report in reports.items():
        for m in report["matches"]:
            if "error" not in m:
                games += 1
                sides[(label, m["map"])][tuple(m["order"])] = int(m["winner"] == 0)
    scores = [sum(s.values()) / 2 for s in sides.values() if len(s) == 2]
    value = llr(scores, p0, p1)
    outcome = "H1" if value >= bounds[1] else "H0" if value <= bounds[0] else None
    return {"llr": value, "pairs": len(scores), "games": games, "outcome": outcome}


def read_results(batch):
    try:
        return json.loads((batch / "results.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def terminate(procs, grace=5.0):
    """End each process's group (run_batched, its run-batch and that one's game workers): SIGTERM, then SIGKILL for
    whatever is left after `grace` seconds. Each group gets its signal before any member can react to another's death,
    so no run_batched records a killed game as failed."""
    for proc in procs:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)
    deadline = monotonic() + grace
    for proc in procs:
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(max(0.0, deadline - monotonic()))
    # A group outlives its leader while any child is still exiting.
    while monotonic() < deadline and any(group_alive(p.pid) for p in procs):
        sleep(0.1)
    for proc in procs:
        if group_alive(proc.pid):
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


def sprt_line(s):
    p0, p1 = s["hypotheses"]
    lo, hi = s["bounds"]
    stops = {"both": "either", "low": "H0 only", "high": "H1 only"}[s["stop"]]
    line = (f"SPRT H0 {p0:g} vs H1 {p1:g} (alpha {s['alpha']:g}, beta {s['beta']:g}, stops on {stops}, "
            f"from {s['min_games']} games): LLR {s['llr']:.2f} in [{lo:.2f}, {hi:.2f}] from {s['pairs']} map pairs "
            f"({2 * s['pairs']} of {s['games']} finished games): "
            f"{(s['outcome'] + ' accepted') if s['outcome'] else 'undecided'}")
    if s["stopped"]:
        line += (f", stopped the run at {s['played']} of {s['scheduled']} games; the win rates are from that partial, "
                 "shuffled sample")
    else:
        line += ", ran to completion"
    others = [f"{h} bound crossed at {g} games" for h, g in s["crossed"].items() if not (s["stopped"] and h == s["outcome"])]
    return line + "".join(f"; {o}" for o in others)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cand", help="Candidate: git ref, or bot directory under bots/")
    parser.add_argument("ref", help="Reference: git ref, or bot directory under bots/")
    parser.add_argument("--name", help="Run name (default: <cand>-vs-<ref>); results in replays/ab/<name>/")
    parser.add_argument("--threads", type=int, default=cpu_slots.SIZE,
                        help=f"Most concurrent matches, as CPU slots allow (default: all {cpu_slots.SIZE})")
    parser.add_argument("--suites", default="ladder,gen,fresh",
                        help="Comma-separated: ladder, gen, fresh, or directories of maps (default: all three)")
    parser.add_argument("--no-test-draft", action="store_true",
                        help="Leave materialised copies' params.h untouched, so each plays its own draft")
    parser.add_argument("--game-timeout", type=float, help="Opt-in native per-game wallclock limit; errors are retained")
    parser.add_argument("--experiment-config", type=Path, help="Per-map native REF runtime config JSON")
    parser.add_argument("--fuel", type=int, help="Fuel per turn, passed to run_batched.py --fuel")
    parser.add_argument("--debug", dest="release", action="store_false",
                        help="Both bots as debug builds, whose debug_block traces run (OOF, SHORTCUT, decision lines), "
                        "instead of release builds as the platform plays them (run_batched.py --release, the default): "
                        "~15%% more CPU a game, and its games differ from release builds'")
    parser.add_argument("--sprt", nargs="?", type=hypotheses, const=(0.50, 0.52), metavar="P0,P1",
                        help="Stop early by a sequential test of CAND's win rate P0 (H0) against P1 (H1) "
                        "(default: 0.50,0.52); the maps play in a seeded random order")
    parser.add_argument("--sprt-alpha", type=error_rate, metavar="A", help="--sprt's false H1 rate (default: 0.05)")
    parser.add_argument("--sprt-beta", type=error_rate, metavar="B", help="--sprt's false H0 rate (default: 0.05)")
    parser.add_argument("--sprt-stop", choices=("both", "low", "high"),
                        help="Which decision stops the run: both, low (accepting H0: not a P1 gain) or high (accepting "
                        "H1); the other is only reported (default: both)")
    parser.add_argument("--sprt-min-games", type=int, metavar="N",
                        help="Never stop before N finished games (default: 200)")
    parser.add_argument("--sprt-seed", type=int, metavar="SEED", help="Seed for the map order (default: 0)")
    parser.add_argument("--keep-replays", type=int, default=1000, metavar="N",
                        help="Replays kept per suite: the first N finished games'; later ones are deleted once their "
                        "out-of-fuel counts are saved (run_batched.py --keep-replays). 0 keeps all (default: 1000)")
    args = parser.parse_args()
    sprt_options = ("sprt_alpha", "sprt_beta", "sprt_stop", "sprt_min_games", "sprt_seed")
    if args.sprt is None:
        if given := [f"--{o.replace('_', '-')}" for o in sprt_options if getattr(args, o) is not None]:
            parser.error(f"{', '.join(given)} only apply with --sprt")
    else:
        if sys.platform == "win32":
            parser.error("--sprt stops suites by process group, which Windows lacks")
        for option, default in zip(sprt_options, (0.05, 0.05, "both", 200, 0)):
            if getattr(args, option) is None:
                setattr(args, option, default)
    cambc_env.check_local_header()
    started = perf_counter()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        sides = [resolve(args.cand), resolve(args.ref)]
        name = slug(args.name or f"{args.cand}-vs-{args.ref}")
        plan, notes = suites([t.strip() for t in args.suites.split(",") if t.strip()])
        if not plan:
            raise ValueError("No suites to play")
        for side, role in zip(sides, ("cand", "ref")):
            if side["kind"] == "git":
                side["path"] = materialise(side, role, name, not args.no_test_draft)
                side["test_draft"] = not args.no_test_draft
    except (ValueError, OSError) as error:
        parser.error(str(error))
    out_dir = ROOT / "replays" / "ab" / name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"A/B {name}: CAND {describe(sides[0])} vs REF {describe(sides[1])}", flush=True)

    def start(label, extra):
        batch = ROOT / "replays" / f"batch-{stamp}-ab-{name}-{slug(label)}"
        log = out_dir / f"{slug(label)}.log"
        command = [sys.executable, str(ROOT / "tools" / "run_batched.py"), str(sides[0]["path"]), str(sides[1]["path"]),
                   "--threads", str(args.threads), "--output", str(batch), *extra]
        if args.game_timeout is not None:
            command += ["--game-timeout", str(args.game_timeout)]
        if args.experiment_config is not None:
            command += ["--experiment-config", str(args.experiment_config.resolve())]
        if args.fuel is not None:
            command += ["--fuel", str(args.fuel)]
        if args.release:
            command.append("--release")
        if args.keep_replays > 0:
            command += ["--keep-replays", str(args.keep_replays)]
        if args.sprt:
            command += ["--shuffle", str(args.sprt_seed)]
        print(f"  {label}: running, log {rel(log)}", flush=True)
        with log.open("w", encoding="utf-8") as stream:
            # With --sprt, each suite is a process group of its own, for terminate().
            return batch, log, subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                                start_new_session=bool(args.sprt))

    # Every suite at once, sharing the CPU slots game by game, so no suite's last games run on a half-idle
    # machine. Not on Windows, where concurrent run-batches break each other's builds (run_batched.py).
    if sys.platform == "win32":
        runs = []
        for label, extra in plan:
            runs.append((label, *start(label, extra)))
            runs[-1][3].wait()
    else:
        runs = [(label, *start(label, extra)) for label, extra in plan]
    killed = set()
    if args.sprt:
        p0, p1 = args.sprt
        bounds = sprt_bounds(args.sprt_alpha, args.sprt_beta)
        stopping = {"both": ("H0", "H1"), "low": ("H0",), "high": ("H1",)}[args.sprt_stop]
        reports, crossed, decision = {}, {}, None
        # Its suites are in their own sessions, so a Ctrl+C or kill reaches only ab.py, which must end them.
        previous = signal.signal(signal.SIGTERM, lambda *_: sys.exit(128 + signal.SIGTERM))
        try:
            while True:
                live = [run for run in runs if run[3].poll() is None]
                for label, batch, _, _ in runs:
                    # A suite still building has none; keep the last good read.
                    if report := read_results(batch):
                        reports[label] = report
                state = sprt_state(reports, p0, p1, bounds)
                if state["outcome"] and state["games"] >= args.sprt_min_games:
                    crossed.setdefault(state["outcome"], state["games"])
                    if live and state["outcome"] in stopping:
                        decision = state
                        break
                if not live:
                    break
                sleep(2)
            if decision:
                print(f"  SPRT: {decision['outcome']} accepted at {decision['games']} games "
                      f"(LLR {decision['llr']:.2f}); stopping {', '.join(run[0] for run in live)}", flush=True)
                terminate([run[3] for run in live])
                killed = {run[0] for run in live}
                for run in live:
                    (run[1] / "results.json.tmp").unlink(missing_ok=True)
        except BaseException:
            terminate([run[3] for run in runs if run[3].poll() is None])
            raise
        finally:
            signal.signal(signal.SIGTERM, previous)
        sprt = {"hypotheses": [p0, p1], "alpha": args.sprt_alpha, "beta": args.sprt_beta, "stop": args.sprt_stop,
                "min_games": args.sprt_min_games, "seed": args.sprt_seed, "bounds": [round(b, 4) for b in bounds],
                **(decision or state), "crossed": crossed}
        sprt["llr"] = round(sprt["llr"], 4)
    results = []
    # Reading every replay's stdout takes ~1.5 s a 512-game suite, so a suite's count is split across processes.
    # Windows allows at most 61 workers.
    pool = ProcessPoolExecutor(min(61, max(len(runs), (os.cpu_count() or 2) - 1)))
    counts = {}
    # --release: bots print no OOF lines, so out-of-fuel turns are the runner's, per match: (turns, games) by bot.
    runner_oof = {}
    for label, batch, log, proc in runs:
        code = proc.wait()
        entry = {"suite": label, "batch": rel(batch), "log": rel(log), "exit": code,
                 "games": 0, "wins": 0, "errors": 0, "failed": [], "oof": None, "early": {"cand": 0, "ref": 0},
                 "handoff": None, "capped": None}
        if args.sprt:
            entry.update(completed=0, scheduled=None)
        try:
            report = json.loads((batch / "results.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            if label not in killed:
                entry["failed"].append({"map": None, "error": f"run_batched exit {code}, no results; see {rel(log)}"})
                entry["errors"] = 1
            results.append(entry)
            continue
        # Only finished matches' replays: a killed game can leave a partial one. oof.count reads a pruned one's
        # saved lines.
        files = sorted(str(batch / Path(m.get("replay") or m["pruned"]).name) for m in report["matches"]
                       if m.get("replay") or m.get("pruned"))
        counts[label] = [pool.submit(oof.count, batch, files[i:i + 48]) for i in range(0, len(files), 48)]
        if args.release:
            played = [m for m in report["matches"] if "winner" in m]
            if all("oof_turns" in m for m in played):
                runner_oof[label] = {k: [sum(m["oof_turns"][i] for m in played), sum(m["oof_turns"][i] > 0 for m in played)]
                                     for i, k in enumerate(("cand", "ref"))}
        entry["errors"] = report["errors"]
        entry["games"] = report["completed"] - report["errors"]
        entry["wins"] = report["wins"][0]
        for m in report["matches"]:
            if "winner" in m and m["rounds"] <= cambc_env.EARLY_ROUNDS:
                entry["early"]["ref" if m["winner"] == 0 else "cand"] += 1
        entry["failed"] = [{"map": Path(m["map"]).name, "cand_side": "AB"[m["order"].index(0)],
                            "error": m["error"]} for m in report["matches"] if "error" in m]
        if args.sprt:
            entry.update(completed=report["completed"], scheduled=report["scheduled"])
        if code and not entry["errors"] and label not in killed:
            entry["errors"] = 1
            entry["failed"].append({"map": None, "error": f"run_batched exit {code}; see {rel(log)}"})
        results.append(entry)
    for entry in results:
        if entry["suite"] in counts:
            try:
                turns, games, handoffs, capped = (collections.Counter() for _ in range(4))
                for part in counts[entry["suite"]]:
                    _, t, g, _, _, h, c = part.result()
                    turns.update(t)
                    games.update(g)
                    handoffs.update(h)
                    capped.update(c)
                entry["oof"] = {"cand": [turns[1], games[1]], "ref": [turns[2], games[2]]}
                if args.release:
                    entry["oof"] = runner_oof.get(entry["suite"])
                    if entry["oof"] is None:
                        entry["oof_error"] = "release builds print no OOF lines, and this runner gave no counts"
                entry["handoff"] = {"cand": handoffs[1], "ref": handoffs[2]}
                entry["capped"] = {"cand": capped[1], "ref": capped[2]}
            except (OSError, KeyError, ValueError) as error:
                entry["oof_error"] = str(error)
    pool.shutdown()

    wall = perf_counter() - started
    games = sum(r["games"] for r in results)
    wins = sum(r["wins"] for r in results)
    errors = sum(r["errors"] for r in results)
    oof_total = {k: [sum(r["oof"][k][i] for r in results if r["oof"]) for i in (0, 1)] for k in ("cand", "ref")}
    early = {k: sum(r["early"][k] for r in results) for k in ("cand", "ref")}
    handoff = {k: sum(r["handoff"][k] for r in results if r["handoff"]) for k in ("cand", "ref")}
    capped = {k: sum(r["capped"][k] for r in results if r["capped"]) for k in ("cand", "ref")}
    lo, hi = wilson(wins, games)
    summary = {
        "name": name, "started": stamp, "wall_seconds": round(wall, 1), "threads": args.threads,
        "fuel": args.fuel, "game_timeout": args.game_timeout, "experiment_config": ({"path": str(args.experiment_config.resolve()), "sha256": hashlib.sha256(args.experiment_config.read_bytes()).hexdigest()} if args.experiment_config else None), "release": args.release, "cand": {**sides[0], "path": rel(sides[0]["path"])},
        "ref": {**sides[1], "path": rel(sides[1]["path"])}, "games": games, "cand_wins": wins,
        "cand_win_pct": round(100 * wins / games, 2) if games else None, "ci95": [round(lo, 2), round(hi, 2)],
        "errors": errors, "oof": oof_total, "early_losses": early, "handoff_failures": handoff, "capped_drafts": capped,
        "notes": notes,
        "suites": results,
    }
    # Engines change outcomes (5.0.1 against 5.0.0: ~7% of games), so runs record which one played them.
    with contextlib.suppress(OSError, IndexError):
        summary["cambc"] = subprocess.run(["cambc", "--version"], capture_output=True, text=True).stdout.split()[-1]
    # A suite without OOF counts (a release build on stock cambc) would read as 0 in the totals.
    if any(r.get("oof_error") for r in results):
        summary["oof_error"] = "; ".join(sorted({r["oof_error"] for r in results if r.get("oof_error")}))
    if args.sprt:
        sprt["stopped"] = any(r["suite"] in killed and r["completed"] != r["scheduled"] for r in results)
        sprt["played"] = sum(r["completed"] for r in results)
        sprt["scheduled"] = sum(r["scheduled"] or 0 for r in results)
        summary["sprt"] = sprt
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    width = max(len(r["suite"]) for r in results)
    lines = [f"CAND {rate(wins, games)}"]
    lines += [f"  {r['suite']:<{width}}  {rate(r['wins'], r['games'])}" + (f", {r['errors']} failed" if r["errors"] else "")
              + (f", {r['completed']}/{r['scheduled'] or '?'} played" if args.sprt and sprt["stopped"] else "")
              for r in results]
    if args.sprt:
        lines.append(sprt_line(sprt))
    lines += notes
    failed = [(r["suite"], f) for r in results for f in r["failed"]]
    lines.append(f"Failed matches: {len(failed)}")
    lines += [f"  {s} {f['map'] or ''} {('CAND=' + f['cand_side']) if f.get('cand_side') else ''}: {f['error']}"
              for s, f in failed[:5]]
    if len(failed) > 5:
        lines.append(f"  ... {len(failed) - 5} more in summary.json")
    lines.append(f"Out-of-fuel turns: CAND {oof_total['cand'][0]} in {oof_total['cand'][1]} games, "
                 f"REF {oof_total['ref'][0]} in {oof_total['ref'][1]} games")
    lines.append(f"Broken draft handoffs (DRAFT-UNFINISHED/PLAN-CHECK): CAND {handoff['cand']} games, REF {handoff['ref']}; "
                 f"lost by round {cambc_env.EARLY_ROUNDS}: CAND {early['cand']}, REF {early['ref']}; "
                 f"capped drafts (DRAFT-CAPPED): CAND {capped['cand']} games, REF {capped['ref']}")
    banner = cambc_env.handoff_banner(early, {"cand": "CAND", "ref": "REF"})
    if banner or any(handoff.values()):
        banner = banner or f"!!! BROKEN DRAFT HANDOFFS: CAND {handoff['cand']}, REF {handoff['ref']} games !!!"
        lines = [banner] + lines + [banner]
    lines.append(f"Wall time: {int(wall // 60)}m{int(wall % 60):02d}s")
    lines.append(f"Results: {rel(out_dir)}/summary.md")
    print("\n".join(lines))

    md = [f"# A/B {name}", "", f"CAND {describe(sides[0])}, `{rel(sides[0]['path'])}`",
          f"REF {describe(sides[1])}, `{rel(sides[1]['path'])}`", "",
          f"Started {stamp}; threads {args.threads}; fuel {args.fuel or 'default'}; "
          f"{'release' if args.release else 'debug'} builds; "
          f"wall {wall / 60:.1f} min", "", *([f"**{banner}**", ""] if banner else []),
          "| Suite | CAND win % | Games | 95% CI | Failed | OOF CAND | OOF REF | Batch |", "|---|---|---|---|---|---|---|---|"]
    for r in results + [{"suite": "**total**", "games": games, "wins": wins, "errors": errors,
                         "oof": oof_total, "batch": ""}]:
        a, b = wilson(r["wins"], r["games"])
        pct = f"{100 * r['wins'] / r['games']:.1f}" if r["games"] else "-"
        o = r["oof"] or {"cand": ["?", "?"], "ref": ["?", "?"]}
        md.append(f"| {r['suite']} | {pct} | {r['games']} | {a:.1f}-{b:.1f} | {r['errors']} | "
                  f"{o['cand'][0]} | {o['ref'][0]} | {('`' + r['batch'] + '`') if r['batch'] else ''} |")
    if args.sprt:
        md += ["", sprt_line(sprt)]
    md += ["", f"Broken draft handoffs: CAND {handoff['cand']} games, REF {handoff['ref']}; lost by round "
                 f"{cambc_env.EARLY_ROUNDS}: CAND {early['cand']}, REF {early['ref']}; capped drafts (DRAFT-CAPPED): "
                 f"CAND {capped['cand']} games, REF {capped['ref']}"]
    md += [""] + [f"- {n}" for n in notes]
    if failed:
        md += ["", "Failed matches:"] + [f"- {s} {f['map'] or ''}: {f['error']}" for s, f in failed]
    (out_dir / "summary.md").write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
