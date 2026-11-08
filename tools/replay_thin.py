"""Bound the replays of A/B batches, finished or still running: keep each batch's oldest N replays and delete the
rest, each only once its match is in the batch's results.json and the file is MIN_AGE minutes old. Before a
replay is deleted its out-of-fuel and handoff lines are saved to the batch's pruned-stdout.jsonl, which
tools/fuel/oof.py (and so ab.py's end-of-run tally) reads in place of the missing replay. A directory holding a
.keep file is skipped, and so is one with an oofj.jsonl (a janitor of its own tallies and deletes it). The replay
janitor (~/bin/replay-janitor.sh) runs this every 15 minutes, for runs started before ab.py bounded its own
(--keep-replays) and for batches of other callers named batch-*-ab-*.

    py tools/replay_thin.py [--keep 1000] [--min-age 10] [--glob 'batch-*-ab-*'] [--dry-run]
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import sys
from time import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "fuel"))
import oof  # noqa: E402

REPLAYS = ROOT / "replays"


def candidates(d, keep, min_age):
    """Replays of batch d to delete: all but the oldest `keep`, recorded in results.json and old enough."""
    try:
        report = json.loads((d / "results.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []  # not started, or a torn read: next time
    recorded = {Path(m["replay"]).name for m in report.get("matches", []) if m.get("replay") and "error" not in m}
    files = []
    with os.scandir(d) as it:
        for e in it:
            if e.name.endswith(".repl26a") and e.is_file(follow_symlinks=False):
                try:
                    files.append((e.stat().st_mtime, e.name))
                except OSError:
                    pass
    files.sort()
    cutoff = time() - 60 * min_age
    return [d / name for mtime, name in files[keep:] if name in recorded and mtime < cutoff]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keep", type=int, default=1000, help="Replays kept per batch (default: 1000)")
    parser.add_argument("--min-age", type=float, default=10, help="Minutes a replay must have existed (default: 10)")
    parser.add_argument("--glob", default="batch-*-ab-*", help="Batch directories under replays/ (default: ab.py's)")
    parser.add_argument("--workers", type=int, default=16, help="Processes reading replays (default: 16)")
    parser.add_argument("--dry-run", action="store_true", help="Only count what would go")
    args = parser.parse_args()
    lock = open(REPLAYS / ".thin.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("replay_thin: another instance is running")
        return 0
    os.nice(10)
    plan = {}
    for d in sorted(REPLAYS.glob(args.glob)):
        # oofj.jsonl: another janitor tallies and deletes this batch's replays itself.
        if d.is_dir() and not (d / ".keep").exists() and not (d / "oofj.jsonl").exists():
            if files := candidates(d, args.keep, args.min_age):
                plan[d] = files
    total = sum(map(len, plan.values()))
    if args.dry_run:
        for d, files in plan.items():
            print(f"{len(files):7} {d.name}")
        print(f"replay_thin: would delete {total} replays in {len(plan)} batches")
        return 0
    deleted = 0
    if plan:
        with ProcessPoolExecutor(args.workers) as pool:
            parts = [pool.submit(oof.thin, d, [str(f) for f in files[i:i + 200]])
                     for d, files in plan.items() for i in range(0, len(files), 200)]
            deleted = sum(p.result() for p in parts)
    print(f"replay_thin: deleted {deleted} of {total} replays in {len(plan)} batches (keep {args.keep})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
