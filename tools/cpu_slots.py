"""Machine-wide CPU slots, so concurrent benches and A/Bs (from any worktree) share the cores instead of each
assuming the whole machine.

The pool is CAMBC_SLOTS slots (default: cores - 2). A slot is an OS lock on a file in the repository's common git
directory, so every worktree sees the same pool and a crashed holder frees its slots. bench.py and run_batched.py
(ab.py, solo.py) hold a slot per game, so concurrent runs can all ask for every slot and share them game by game;
on Windows run_batched.py instead takes what is free at its start, up to --threads, and holds it for the run.

Fair share (Linux; tools/fastengine/runner's fastrunner mirrors it, Slots in src/lib.rs): slots are shared between
groups, not processes. A group is a job: CAMBC_SLOT_GROUP, set on import to `job-<pid>` unless already set, so a
tool and every process it starts (ab.py's suites, their fastrunner run-batches) are one group. CAMBC_SLOT_WEIGHT
(default 1; the draft lab 2) scales its share. A group keeps a free slot it takes only while it holds less than its
share (the pool times its weight over the weights of the groups holding or waiting), or when no other waiting group
holds less than its own; otherwise it hands it back and waits a little longer, so a group below its share gets the
next free slot. A lone job still takes every slot, and a running game is never stopped: shares settle as games end.
Each held slot file holds its group's name; DIR/members/ has a file per process (locked while it lives: group,
weight, whether it waits); DIR/fair.lock orders the decisions. Holders without the protocol count as group `legacy`.
"""
import collections
import contextlib
import os
import random
import subprocess
import sys
import threading
import tempfile
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
FAIR = sys.platform != "win32"
GROUP = "".join("_" if c.isspace() else c for c in os.environ.setdefault("CAMBC_SLOT_GROUP", f"job-{os.getpid()}"))


def _dir():
    if os.environ.get("CAMBC_SLOT_DIR"):  # another pool (tests)
        d = Path(os.environ["CAMBC_SLOT_DIR"])
        d.mkdir(parents=True, exist_ok=True)
        return d
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
            if FAIR:
                f.truncate(0)
            _unlock(f)
        finally:
            f.close()


_member = None
_waiting = 0
_member_lock = threading.Lock()


def _weight():
    try:
        w = float(os.environ.get("CAMBC_SLOT_WEIGHT", "1"))
    except ValueError:
        return 1.0
    return w if 0 < w < float("inf") else 1.0


def _write_member():
    _member.seek(0)
    _member.truncate()
    _member.write(f"{GROUP}\t{_weight()}\t{1 if _waiting else 0}\n".encode())
    _member.flush()


def _set_waiting(delta):
    """Count this process's waiting acquires; its member file says whether any wait. Registers it first."""
    global _member, _waiting
    with _member_lock:
        if _member is None:
            members = DIR / "members"
            members.mkdir(exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=f"member-{os.getpid()}-", dir=DIR)
            f = os.fdopen(fd, "w+b")
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(f"{GROUP}\t{_weight()}\t{1 if _waiting else 0}\n".encode())
                f.flush()
                # Scanners unlink unlocked members: publish only after the lifetime lock and record exist.
                os.rename(tmp, members / Path(tmp).name)
            except BaseException:
                f.close()
                Path(tmp).unlink(missing_ok=True)
                raise
            _member = f
        was = _waiting > 0
        _waiting += delta
        if was != (_waiting > 0):
            _write_member()


def _claim(i, f):
    """Under DIR/fair.lock: whether to keep slot i (just locked as f), writing our group into it if so."""
    with open(DIR / "fair.lock", "a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        held = collections.Counter()
        for j in range(SIZE):
            if j == i:
                continue
            try:
                g = open(DIR / f"slot-{j:02}", "rb")
            except FileNotFoundError:
                continue
            with g:
                try:
                    fcntl.flock(g.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    continue  # free (flock on close)
                except OSError:
                    held[g.read().decode(errors="replace").strip() or "legacy"] += 1
        weight, waiting = {}, set()
        for path in (DIR / "members").iterdir() if (DIR / "members").is_dir() else ():
            try:
                m = open(path, "rb")
            except OSError:
                continue
            with m:
                try:
                    fcntl.flock(m.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    path.unlink(missing_ok=True)  # its process is gone
                    continue
                except OSError:
                    parts = m.read().decode(errors="replace").rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            try:
                w = float(parts[1])
            except ValueError:
                w = 1.0
            weight[parts[0]] = max(weight.get(parts[0], w), w)
            if parts[2] == "1":
                waiting.add(parts[0])
        weight[GROUP] = max(weight.get(GROUP, 0.0), _weight())
        active = set(held) | waiting | {GROUP}
        total = sum(weight.get(g, 1.0) for g in active)
        share = {g: SIZE * weight.get(g, 1.0) / total for g in active}
        ok = held[GROUP] < share[GROUP] - 1e-9 or not any(g != GROUP and held[g] < share[g] - 1e-9 for g in waiting)
        if ok:
            f.truncate(0)
            f.write(GROUP.encode())
            f.flush()
        return ok


def acquire(want, least=1, poll=0.25):
    """Up to `want` slots: whatever is free now and fair share allows, waiting until at least `least` are held."""
    want, least = max(1, min(want, SIZE)), max(1, min(least, want, SIZE))
    held = []
    waiting = False
    if FAIR:
        _set_waiting(0)  # registers this process, so its weight counts before it ever waits
    try:
        while True:
            denied = False
            for i in random.sample(range(SIZE), SIZE):
                if len(held) >= want or denied:
                    break
                if all(Path(h.name).name != f"slot-{i:02}" for h in held) and (f := _try(i)):
                    if not FAIR:
                        held.append(f)
                    elif _claim(i, f):
                        held.append(f)
                    else:
                        release([f])
                        denied = True
            if len(held) >= least:
                return held
            if FAIR and not waiting:
                _set_waiting(1)
                waiting = True
            # Refused by fair share: wait longer, so a waiting group below its share takes the slot first.
            time.sleep(max(poll, 0.02 + 0.03 * random.random()) if denied else poll)
    finally:
        if waiting:
            _set_waiting(-1)


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
