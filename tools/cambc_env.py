"""Environment for cambc processes that play matches.

Every match process compiles both bots' WASM with Cranelift, ~2 CPU-seconds a bot, on a rayon pool of one
thread per core: about 80% of a match's CPU on 2026-10-29 (5.95 CPU-s a match, 1.17 with the modules cached).
CAMBC_WASMTIME_CACHE (a directory) makes cambc keep compiled modules in wasmtime's cache, keyed by the
module's bytes, so a bot compiles once; replays are byte-identical either way. RAYON_NUM_THREADS=1 keeps a
cache miss from starting a thread per core in every concurrent match. run-batch passes both to its matches.
"""
import os
import subprocess
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
