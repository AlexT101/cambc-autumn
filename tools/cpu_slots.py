"""Machine-wide CPU slots, so concurrent benches and A/Bs (from any worktree) share the cores instead of each
assuming the whole machine.

The pool is CAMBC_SLOTS slots (default: cores - 2). A slot is an OS lock on a file in the repository's common git
directory, so every worktree sees the same pool and a crashed holder frees its slots. bench.py and run_batched.py
(ab.py, solo.py) hold a slot per game, so concurrent runs can all ask for every slot and share them game by game;
on Windows run_batched.py instead takes what is free at its start, up to --threads, and holds it for the run.
"""
import contextlib
import os
import random
import subprocess
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    import msvcrt

    def _lock(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _lock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

SIZE = int(os.environ.get("CAMBC_SLOTS", max(1, (os.cpu_count() or 4) - 2)))


def _dir():
    root = Path(__file__).resolve().parents[1]
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root, capture_output=True, text=True)
    base = Path(common.stdout.strip()) if common.returncode == 0 else root
    if not base.is_absolute():
        base = root / base
    d = base / "cambc-slots"
    d.mkdir(parents=True, exist_ok=True)
    return d


DIR = _dir()


def _try(i):
    f = open(DIR / f"slot-{i:02}", "a+b")
    f.seek(0)
    try:
        _lock(f)
        return f
    except OSError:
        f.close()
        return None


def release(handles):
    for f in handles:
        try:
            _unlock(f)
        finally:
            f.close()


def acquire(want, least=1, poll=0.25):
    """Up to `want` slots: whatever is free now, waiting until at least `least` are held."""
    want, least = max(1, min(want, SIZE)), max(1, min(least, want, SIZE))
    held = []
    while True:
        for i in random.sample(range(SIZE), SIZE):
            if len(held) >= want:
                break
            if all(Path(h.name).name != f"slot-{i:02}" for h in held) and (f := _try(i)):
                held.append(f)
        if len(held) >= least:
            return held
        time.sleep(poll)


@contextlib.contextmanager
def exclusive(path, poll=0.2):
    """An OS lock on `path` for the duration of the block, waiting for any other holder."""
    f = open(path, "a+b")
    try:
        while True:
            f.seek(0)
            try:
                _lock(f)
                break
            except OSError:
                time.sleep(poll)
        try:
            yield
        finally:
            _unlock(f)
    finally:
        f.close()


@contextlib.contextmanager
def slot():
    """One slot for the duration of the block."""
    held = acquire(1)
    try:
        yield
    finally:
        release(held)
