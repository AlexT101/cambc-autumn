#!/usr/bin/env python3
"""Time one match under several runners, interleaved (ABCABC...), pinned to one CPU; prints median wall and CPU.

    python3 tools/fastengine/runner/scripts/bench.py BOT_A BOT_B MAP [--cpu 1] [--reps 5] [--turbo /abs/turbo.so]
        [--modes exact,approx] [--release] [--no-stock]
"""
import argparse
import os
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
import cambc_env  # noqa: E402

FAST = ROOT / "tools" / "fastengine" / "runner" / "fastrunner"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("map")
    ap.add_argument("--cpu", default="1")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--turbo")
    ap.add_argument("--modes", default="exact")
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--no-stock", action="store_true")
    args = ap.parse_args()
    bot = lambda n: (Path(n) if Path(n).is_dir() else ROOT / "bots" / n).resolve()
    mp = Path(args.map) if Path(args.map).is_file() else ROOT / "maps" / f"{args.map}.map26a"
    tmp = Path(tempfile.mkdtemp(prefix="fastbench-", dir=os.environ.get("TMPDIR")))
    manifest = tmp / "m.txt"
    manifest.write_text(f"{bot(args.a)} {bot(args.b)} {mp.resolve()} {tmp / 'g.repl26a'}\n")
    runners = []
    if not args.no_stock:
        runners.append(("stock", ["cambc", "run-batch", str(manifest)], {}))
    if args.turbo:
        runners.append(("turbo", ["cambc", "run-batch", str(manifest)], {"LD_PRELOAD": args.turbo}))
    for m in args.modes.split(","):
        if m:
            # MODE or MODE:K=V:K=V (extra environment)
            parts = m.split(":")
            env = {"FASTRUNNER_MODE": parts[0], **dict(p.split("=", 1) for p in parts[1:])}
            runners.append((f"fast-{m}", [str(FAST), "run-batch", str(manifest)], env))
    times = {n: [] for n, _, _ in runners}
    for _ in range(args.reps):
        for name, cmd, extra in runners:
            env = cambc_env.env()
            env.update(extra)
            full = ["taskset", "-c", args.cpu, *cmd, "--color", "never"] + (["--release"] if args.release else [])
            (tmp / "g.repl26a").unlink(missing_ok=True)
            c0 = resource.getrusage(resource.RUSAGE_CHILDREN)
            t0 = time.perf_counter()
            r = subprocess.run(full, env=env, capture_output=True, text=True)
            wall = time.perf_counter() - t0
            c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu = (c1.ru_utime + c1.ru_stime) - (c0.ru_utime + c0.ru_stime)
            if r.returncode:
                print(name, "failed:", r.stdout[-500:], r.stderr[-500:])
            times[name].append((wall, cpu))
    base = None
    for name, ts in times.items():
        w = statistics.median(t[0] for t in ts)
        c = statistics.median(t[1] for t in ts)
        base = base or w
        print(f"{name:12s} wall {w:.3f}s  cpu {c:.3f}s  speedup {base / w:.2f}x  (walls {', '.join(f'{t[0]:.3f}' for t in ts)})")


if __name__ == "__main__":
    main()
