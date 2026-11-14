"""Environment for cambc processes that play matches.

Every match process compiles both bots' WASM with Cranelift, ~2 CPU-seconds a bot, on a rayon pool of one
thread per core: about 80% of a match's CPU on 2026-10-29 (5.95 CPU-s a match, 1.17 with the modules cached).
CAMBC_WASMTIME_CACHE (a directory) makes cambc keep compiled modules in wasmtime's cache, keyed by the
module's bytes, so a bot compiles once; replays are byte-identical either way. RAYON_NUM_THREADS=1 keeps a
cache miss from starting a thread per core in every concurrent match. run-batch passes both to its matches.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cpu_slots

ROOT = Path(__file__).resolve().parents[1]
# Beside the CPU slots in the git common dir, so every worktree shares it.
CACHE = cpu_slots.DIR.parent / "cambc-wasmtime"


def env(serial=True):
    """os.environ for a cambc match process, with the compile cache (unless set) and, if serial, one compile
    thread (a parallel compile only shortens the wall time of a lone match, at ~50% more CPU)."""
    e = {**os.environ, "NO_COLOR": "1"}
    e.setdefault("CAMBC_WASMTIME_CACHE", str(CACHE))
    if serial:
        e.setdefault("RAYON_NUM_THREADS", "1")
    else:
        e.pop("RAYON_NUM_THREADS", None)
    return e


def warm(cli, bot, map_path, options=()):
    """Compile a built bot into the cache with one round of it against itself, on all cores (~0.4 s), so a
    batch's first wave of matches doesn't each compile it. Returns whether the match ran."""
    with tempfile.TemporaryDirectory() as tmp:
        manifest = Path(tmp) / "warm.txt"
        manifest.write_text(f"{Path(bot).as_posix()} {Path(bot).as_posix()} {Path(map_path).as_posix()} "
                            f"{Path(tmp).as_posix()}/warm.repl26a\n", encoding="utf-8")
        done = subprocess.run([cli, "run-batch", str(manifest), "--rounds", "1", "--log-limit", "0", *options],
                              cwd=ROOT, env=env(serial=False), capture_output=True)
    return done.returncode == 0


# Local builds compile against sdk/cpp, so bots find this header there and nowhere on the platform: with it, a broken
# draft handoff (an unfinished draft, or no usable plan) resigns in round 1 and prints DRAFT-UNFINISHED or PLAN-CHECK.
LOCAL_HEADER = ROOT / "sdk" / "cpp" / "cambc_local.h"
# Games over by this round: a resign (normal play never ends this early), counted against the side that lost.
EARLY_ROUNDS = 5


def check_local_header():
    """Warns, loudly, if bots built now would not fail on a broken draft handoff."""
    if not LOCAL_HEADER.is_file():
        print(f"WARNING: {LOCAL_HEADER} is missing, so bots built now fall back silently on a broken draft handoff "
              "instead of resigning", file=sys.stderr, flush=True)


def handoff_banner(counts, names):
    """A prominent line for games lost by EARLY_ROUNDS ({side: count}, sides named by names), or None if there were none."""
    if not any(counts.get(k) for k in names):
        return None
    parts = ", ".join(f"{names[k]} {counts.get(k, 0)}" for k in names)
    return (f"!!! EARLY LOSSES (by round {EARLY_ROUNDS}; a broken draft handoff resigns, DRAFT-UNFINISHED or "
            f"PLAN-CHECK in the loser's stdout): {parts} !!!")
