"""Environment for cambc processes that play matches.

Every match process compiles both bots' WASM with Cranelift, ~2 CPU-seconds a bot, on a rayon pool of one
thread per core: about 80% of a match's CPU on 2026-10-29 (5.95 CPU-s a match, 1.17 with the modules cached).
CAMBC_WASMTIME_CACHE (a directory) makes cambc keep compiled modules in wasmtime's cache, keyed by the
module's bytes, so a bot compiles once; replays are byte-identical either way. RAYON_NUM_THREADS=1 keeps a
cache miss from starting a thread per core in every concurrent match. run-batch passes both to its matches.

CAMBC_TURBO (opt-in) preloads tools/fastengine/turbo's library into cambc, which patches cambc 4.0.0 in-process for
~2x speed with byte-identical replays (research/fastengine/DESIGN.md): 1 builds it into the git common dir's
cambc-turbo/ (rebuilt when turbo.c changes), an absolute path names a built one. Linux x86-64 only; elsewhere, and on
any other cambc build (the library checks the build-id), cambc runs stock.
"""
import hashlib
import os
import platform
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import cpu_slots

ROOT = Path(__file__).resolve().parents[1]
# Beside the CPU slots in the git common dir, so every worktree shares it.
CACHE = cpu_slots.DIR.parent / "cambc-wasmtime"


TURBO_SRC = ROOT / "tools" / "fastengine" / "turbo" / "turbo.c"


def turbo_library():
    """The library CAMBC_TURBO asks for, built if need be, or None (unset, 0, another platform, a failed build)."""
    want = os.environ.get("CAMBC_TURBO", "")
    if want in ("", "0") or sys.platform != "linux" or platform.machine() not in ("x86_64", "AMD64"):
        return None
    if want != "1":
        if Path(want).is_absolute() and Path(want).is_file():
            return want
        print(f"CAMBC_TURBO={want!r} is not 0, 1 or an absolute path to the library; cambc runs stock", file=sys.stderr)
        return None
    source = TURBO_SRC.read_bytes()
    lib = cpu_slots.DIR.parent / "cambc-turbo" / f"turbo-{hashlib.sha256(source).hexdigest()[:16]}.so"
    if not lib.is_file():
        lib.parent.mkdir(parents=True, exist_ok=True)
        tmp = lib.with_suffix(f".{os.getpid()}.tmp")
        try:
            built = subprocess.run([*shlex.split(os.environ.get("CC", "cc")), "-O2", "-shared", "-fPIC", "-o", str(tmp), str(TURBO_SRC)],
                                   capture_output=True, text=True)
            error = built.stderr if built.returncode else None
        except OSError as e:
            error = str(e)
        if error is not None:
            print(f"CAMBC_TURBO: building {TURBO_SRC.name} failed, cambc runs stock:\n{error}", file=sys.stderr)
            tmp.unlink(missing_ok=True)
            return None
        os.replace(tmp, lib)  # atomic: concurrent builders race harmlessly
    return str(lib)


def env(serial=True):
    """os.environ for a cambc match process, with the compile cache (unless set) and, if serial, one compile
    thread (a parallel compile only shortens the wall time of a lone match, at ~50% more CPU), and CAMBC_TURBO's
    library preloaded."""
    e = {**os.environ, "NO_COLOR": "1"}
    e.setdefault("CAMBC_WASMTIME_CACHE", str(CACHE))
    if serial:
        e.setdefault("RAYON_NUM_THREADS", "1")
    else:
        e.pop("RAYON_NUM_THREADS", None)
    lib = turbo_library()
    if lib:
        e["LD_PRELOAD"] = f"{lib} {e['LD_PRELOAD']}" if e.get("LD_PRELOAD") else lib
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
