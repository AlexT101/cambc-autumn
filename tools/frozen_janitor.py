"""Prune build caches by last use: run_batched.py's frozen bot copies (replays/frozen/<hash>/) and the fast runner's
compile cache (~/.cache/fastrunner: modules/*.cwasm, native/*.so, draftmem/*.bin, and dead builders' leftovers).
A dry run unless --delete.

    py tools/frozen_janitor.py [--keep-days 7] [--only frozen|cache] [--list] [--delete]

An entry goes once it has not been used for --keep-days and no running process refers to it.
- Last use is the newest mtime of the entry, or for a file also its atime (a frozen copy: its directories, which
  run_batched.py touches on each reuse, and its built wasm, which every game reads). The root mounts relatime, so
  atime lags by up to a day: --keep-days is at least 2.
- A running process refers to an entry when its command line, working directory, open files or mapped libraries name
  it, when a manifest it names lists it (a run-batch manifest, run_batched.py's --output DIR/manifest.txt), or, for a
  frozen copy, when it names a bot directory whose source hashes to that copy (a batch about to freeze or reuse it).
  Every process is scanned, worktrees' included: they share the runner cache.
- A frozen copy whose build.lock is held is skipped; one being deleted is renamed away first, so run_batched.py never
  sees half of one (a batch that wants it again makes a new copy).
A deleted frozen copy costs its next batch a copy and a build (~25 s); a deleted library, its next game a native
compile (~7 s).
"""
import argparse
import contextlib
import fcntl
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import run_batched  # noqa: E402

FROZEN = run_batched.FROZEN
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "fastrunner"
CACHE_FILES = {"modules": ".cwasm", "native": ".so", "draftmem": ".bin"}
HASH = re.compile(r"/replays/frozen/([0-9a-f]{12})(?:/|$)")
# A builder's work dir (.KEY.PID) or temporary file (.HASH.PID.tmp) in the cache, by the pid that made it.
LEFTOVER = re.compile(r"^\.[0-9a-f]{32}[^.]*\.(\d+)(?:\.tmp)?$")
TRASH = re.compile(r"^\.trash-[0-9a-f]{12}-(\d+)$")


def last_use(*paths):
    """The newest use of paths: a file's mtime or atime, a directory's mtime (listing one, as this scan does, bumps its
    atime; stat leaves a file's alone)."""
    t = 0.0
    for p in paths:
        with contextlib.suppress(OSError):
            st = os.stat(p)
            t = max(t, st.st_mtime, 0 if stat.S_ISDIR(st.st_mode) else st.st_atime)
    return t


def size(path):
    if path.is_file():
        return path.stat().st_blocks * 512
    total = 0
    for base, dirs, files in os.walk(path):
        for f in files:
            with contextlib.suppress(OSError):
                total += os.lstat(os.path.join(base, f)).st_blocks * 512
    return total


def bot_dirs(token, cwd):
    """Bot directories a command-line token may name: a path (from the process's cwd) or a name under its bots/."""
    if not token or token.startswith("-") or len(token) > 4096:
        return []
    out = []
    for p in (Path(cwd) / token, Path(cwd) / "bots" / token):
        with contextlib.suppress(OSError):
            if (p / "src").is_dir() and FROZEN not in p.resolve().parents:
                out.append(p.resolve())
    return out


def references():
    """(strings naming paths that running processes use, bot directories their command lines name)."""
    names, bots = set(), set()
    for pid in filter(str.isdigit, os.listdir("/proc")):
        if int(pid) == os.getpid():
            continue
        proc = Path("/proc") / pid
        try:
            argv = (proc / "cmdline").read_bytes().decode(errors="replace").split("\0")
            cwd = os.readlink(proc / "cwd")
        except OSError:
            continue
        names.update(argv)
        names.add(cwd)
        with contextlib.suppress(OSError):
            for fd in os.listdir(proc / "fd"):
                with contextlib.suppress(OSError):
                    names.add(os.readlink(proc / "fd" / fd))
        with contextlib.suppress(OSError):
            for line in (proc / "maps").read_text(errors="replace").splitlines():
                if "/" in line:
                    names.add(line[line.index("/"):])
        batch = any(Path(t).name in ("ab.py", "run_batched.py", "solo.py") for t in argv)
        for i, token in enumerate(argv):
            path = Path(cwd) / token if token and not token.startswith("-") else None
            manifests = []
            with contextlib.suppress(OSError, ValueError):
                if path and path.is_file() and path.suffix == ".txt" and path.stat().st_size < 64 << 20:
                    manifests.append(path)
                elif path and path.is_dir() and i and argv[i - 1] == "--output":
                    manifests.append(path / "manifest.txt")
            for m in manifests:
                with contextlib.suppress(OSError):
                    names.update(m.read_text(errors="replace").split())
            if batch:
                bots.update(bot_dirs(token, cwd))
    return names, bots


def frozen_candidates(cutoff, names, bots, notes):
    live = {m.group(1) for n in names if str(FROZEN) in n for m in [HASH.search(n)] if m}
    for bot in bots:
        with contextlib.suppress(OSError):
            live.add(run_batched.source_hash(bot))
    out = []
    for d in sorted(FROZEN.iterdir()) if FROZEN.is_dir() else ():
        if (m := TRASH.match(d.name)) and not Path("/proc", m.group(1)).exists():
            out.append(d)  # a janitor killed while deleting it
        if not d.is_dir() or d.name.startswith(".") or d.name in live:
            continue
        copies = [c for c in d.iterdir() if c.is_dir() and not c.name.startswith(".")]
        if not copies:
            # A staging copy only, or a half-deleted entry: by its own age.
            if last_use(d) < cutoff:
                out.append(d)
            continue
        wasm = [w for c in copies for w in (c / ".cambc").glob("build*/bot*.wasm")]
        if last_use(d, *copies, *wasm) < cutoff:
            out.append(d)
    notes.append(f"frozen: {len(live)} copies in use by running processes")
    return out


def cache_candidates(cutoff, names, notes):
    used = {n for n in names if str(CACHE) in n}
    out = []
    for sub, suffix in CACHE_FILES.items():
        d = CACHE / sub
        if not d.is_dir():
            continue
        with os.scandir(d) as it:
            for e in it:
                path = Path(e.path)
                if str(path) in used:
                    continue
                if e.name.endswith(suffix) and not e.name.startswith(".") and e.is_file(follow_symlinks=False):
                    if last_use(path) < cutoff:
                        out.append(path)
                elif (m := LEFTOVER.match(e.name)) and not Path("/proc", m.group(1)).exists() and last_use(path) < cutoff:
                    out.append(path)
    notes.append(f"cache: {len(used)} paths in use by running processes")
    return out


def remove_frozen(d):
    """Delete frozen copy d unless a build holds its lock; renamed first so no batch sees part of it."""
    if TRASH.match(d.name):
        shutil.rmtree(d, ignore_errors=True)
        return not d.exists()
    lock = d / "build.lock"
    try:
        f = open(lock, "a+b") if lock.exists() else None
    except OSError:
        return False
    try:
        if f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                return False
        trash = d.parent / f".trash-{d.name}-{os.getpid()}"
        os.rename(d, trash)
    finally:
        if f:
            f.close()
    shutil.rmtree(trash, ignore_errors=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keep-days", type=float, default=7, help="Keep what was used this recently (default: 7, at least 2)")
    parser.add_argument("--only", choices=("frozen", "cache"), help="Only replays/frozen or only the runner cache")
    parser.add_argument("--list", action="store_true", help="Print every entry that would go")
    parser.add_argument("--delete", action="store_true", help="Delete them (default: a dry run)")
    args = parser.parse_args()
    if args.keep_days < 2:
        parser.error("--keep-days must be at least 2: atime, part of the last-use read, lags by up to a day")
    cutoff = time.time() - 86400 * args.keep_days
    names, bots = references()
    notes = []
    plan = {}
    if args.only in (None, "frozen"):
        plan["frozen"] = frozen_candidates(cutoff, names, bots, notes)
    if args.only in (None, "cache"):
        plan["cache"] = cache_candidates(cutoff, names, notes)
    # A process may have started since the scan: look again just before deleting.
    if args.delete:
        names, bots = references()
        again = {}
        if "frozen" in plan:
            again["frozen"] = set(frozen_candidates(cutoff, names, bots, []))
        if "cache" in plan:
            again["cache"] = set(cache_candidates(cutoff, names, []))
        plan = {k: [p for p in v if p in again[k]] for k, v in plan.items()}
    for kind, paths in plan.items():
        total, gone = 0, 0
        for p in paths:
            n = size(p)
            if args.list:
                print(f"{n / 2**20:10.1f} MB  {p}")
            if args.delete:
                if kind == "frozen":
                    ok = remove_frozen(p)
                else:
                    with contextlib.suppress(OSError):
                        shutil.rmtree(p) if p.is_dir() else p.unlink()
                    ok = not p.exists()
                if not ok:
                    continue
                gone += 1
            total += n
        verb = "deleted" if args.delete else "would delete"
        print(f"{kind}: {verb} {gone if args.delete else len(paths)} entries, {total / 2**30:.1f} GB "
              f"(unused for {args.keep_days:g} days)")
    for note in notes:
        print(note)
    if not args.delete:
        print("dry run: pass --delete to delete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
