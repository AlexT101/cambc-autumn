#!/usr/bin/env python3
"""Play the same games with stock cambc and with fastrunner (one or more modes); report replay identity, winner
agreement, bot A's win rate under each runner (Wilson 95% CI, and the paired difference's CI), and CPU/wall time.

    python3 tools/fastengine/runner/scripts/compare.py BOT_A BOT_B --out DIR [--suites ladder,gen] [--maps N]
        [--jobs 4] [--cpus 8-11] [--modes exact,approx] [--release] [--rounds N] [--no-stock] [--turbo /abs/turbo.so]

Every map is played from both sides. Stock runs `cambc run-batch` with tools/cambc_env.py's environment; fastrunner
runs `tools/fastengine/runner/fastrunner run-batch` with FASTRUNNER_MODE set. Results are cached per runner in
DIR/<runner>/ (delete a directory to replay it). Debug builds unless --release (tools/ab.py plays debug builds).
"""
import argparse
import math
import os
import re
import resource
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import cambc_env  # noqa: E402

FAST = ROOT / "tools" / "fastengine" / "runner" / "fastrunner"
STATUS = re.compile(r"^\[.\] (STARTING|TEAM ([AB]) WIN \(.*?\)|FAILED: (.*?))  .*?(?:Round (\d+)/\d+)?\s*$")
REPLAY = re.compile(r"^\s+Replay: (.+?)\s*$")


def suite_maps(token, limit):
    if token == "ladder":
        maps = sorted((ROOT / "maps").glob("*.map26a"))
    elif token == "gen":
        maps = sorted((ROOT / "maps" / "gen").glob("*.map26a"))
    elif token == "gen-s1":
        maps = sorted((ROOT / "maps" / "gen-s1").rglob("*.map26a"))
    else:
        maps = sorted(Path(token).resolve().rglob("*.map26a"))
    return maps[:limit] if limit else maps


def bot_path(name):
    p = Path(name)
    return (p if p.is_dir() else ROOT / "bots" / name).resolve()


def run(runner, games, out, args):
    """Play games [(key, a, b, map)] into out/<key>.repl26a; returns {key: (winner 'A'/'B'/None, rounds)}, cpu, wall."""
    out.mkdir(parents=True, exist_ok=True)
    done = out / "results.txt"
    if done.exists():
        res = {}
        for line in done.read_text().splitlines():
            k, w, r = line.split("\t")
            res[k] = (None if w == "-" else w, int(r))
        meta = (out / "time.txt").read_text().split()
        return res, float(meta[0]), float(meta[1])
    manifest = out / "manifest.txt"
    manifest.write_text("".join(f"{a} {b} {m} {out / f'{k}.repl26a'}\n" for k, a, b, m in games), encoding="utf-8")
    env = cambc_env.env()
    if runner == "stock":
        cmd = ["cambc", "run-batch", str(manifest)]
    elif runner == "turbo":
        cmd = ["cambc", "run-batch", str(manifest)]
        env["LD_PRELOAD"] = args.turbo
    else:
        cmd = [str(FAST), "run-batch", str(manifest)]
        env["FASTRUNNER_MODE"] = runner.removeprefix("fast-")
    cmd = ["taskset", "-c", args.cpus, *cmd, "--jobs", str(args.jobs), "--color", "never"]
    if args.release:
        cmd.append("--release")
    if args.rounds:
        cmd += ["--rounds", str(args.rounds)]
    c0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.time()
    r = subprocess.run(cmd, env=env, cwd=ROOT, capture_output=True, text=True)
    wall = time.time() - t0
    c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (c1.ru_utime + c1.ru_stime) - (c0.ru_utime + c0.ru_stime)
    (out / "run.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    res, status = {}, None
    for line in r.stdout.splitlines():
        if m := STATUS.match(line):
            status = m
            continue
        m = REPLAY.match(line)
        if not m or status is None:
            continue
        key = Path(m.group(1)).stem
        kind, team, fail, rounds = status.groups()
        status = None
        if kind == "STARTING":
            continue
        res[key] = (team, int(rounds or 0))
    done.write_text("".join(f"{k}\t{w or '-'}\t{n}\n" for k, (w, n) in res.items()))
    (out / "time.txt").write_text(f"{cpu} {wall}\n")
    return res, cpu, wall


def members(path):
    try:
        with zipfile.ZipFile(path) as z:
            return {n: z.read(n) for n in z.namelist()}
    except (OSError, zipfile.BadZipFile):
        return None


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (p, c - h, c + h)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bot_a")
    ap.add_argument("bot_b")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--suites", default="ladder,gen")
    ap.add_argument("--maps", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--cpus", default="8-11")
    ap.add_argument("--modes", default="exact")
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--rounds", type=int, default=0)
    ap.add_argument("--no-stock", action="store_true")
    ap.add_argument("--turbo")
    args = ap.parse_args()
    a, b = bot_path(args.bot_a), bot_path(args.bot_b)
    games = []
    for s in args.suites.split(","):
        for m in suite_maps(s, args.maps):
            stem = f"{Path(s).name}-{m.stem}"
            games.append((f"{stem}-12", a, b, m))
            games.append((f"{stem}-21", b, a, m))
    runners = ([] if args.no_stock else ["stock"]) + (["turbo"] if args.turbo else []) + [f"fast-{m}" for m in args.modes.split(",") if m]
    results = {}
    for rn in runners:
        res, cpu, wall = run(rn, games, args.out / rn, args)
        results[rn] = res
        n = len(res)
        print(f"{rn:12s} {n} games  cpu {cpu:7.1f}s ({cpu / max(n, 1):.3f}/game)  wall {wall:6.1f}s  "
              f"({3600 * n / max(wall, 1e-9):.0f} games/h)")
    # bot A's result per game: 1 if bot A won
    def a_won(key, w):
        return (w == "A") if key.endswith("-12") else (w == "B")
    for rn in runners:
        res = results[rn]
        ok = [k for k, _, _, _ in games if res.get(k, (None,))[0]]
        wins = sum(a_won(k, res[k][0]) for k in ok)
        p, lo, hi = wilson(wins, len(ok))
        print(f"{rn:12s} bot A ({a.name}) wins {wins}/{len(ok)} = {100 * p:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}]"
              f"  failed {len(games) - len(ok)}")
    if "stock" in results:
        for rn in runners:
            if rn == "stock":
                continue
            same_bundle = same_play = same_replay = same_winner = both = 0
            diff, differing = [], []
            for k, *_ in games:
                ws, wf = results["stock"].get(k, (None, 0)), results[rn].get(k, (None, 0))
                if ws[0] is None or wf[0] is None:
                    continue
                both += 1
                same_winner += ws[0] == wf[0]
                diff.append(int(a_won(k, wf[0])) - int(a_won(k, ws[0])))
                ms = members(args.out / "stock" / f"{k}.repl26a")
                mf = members(args.out / rn / f"{k}.repl26a")
                if ms is not None and mf is not None:
                    same_bundle += ms == mf
                    same_replay += ms.get("replay.repl26a") == mf.get("replay.repl26a")
                    # fastrunner records no debug drawings; everything else must match.
                    play = {n for n in ms.keys() | mf.keys() if not n.endswith(".debug")}
                    bad = sorted(n for n in play if ms.get(n) != mf.get(n))
                    same_play += not bad
                    if bad:
                        differing.append(f"{k}: {' '.join(bad)}")
            mean = sum(diff) / max(len(diff), 1)
            sd = math.sqrt(sum((d - mean) ** 2 for d in diff) / max(len(diff) - 1, 1))
            half = 1.96 * sd / math.sqrt(max(len(diff), 1))
            (args.out / f"differing-{rn}.txt").write_text("".join(d + "\n" for d in differing), encoding="utf-8")
            print(f"{rn:12s} vs stock: bundles identical {same_bundle}/{both}, all but .debug {same_play}/{both}, "
                  f"replays identical {same_replay}/{both}, "
                  f"winner agrees {same_winner}/{both}; win-rate diff {100 * mean:+.1f} pts [{100 * (mean - half):+.1f}, "
                  f"{100 * (mean + half):+.1f}]")


if __name__ == "__main__":
    main()
