"""Out-of-fuel play turns per bot in run_batched.py batches (local builds print an `OOF round phase` line for each),
and broken draft handoffs: local builds resign on one, printing a line starting with one of HANDOFF.

    py tools/fuel/oof.py replays/batch-A replays/batch-B ...

A thinned replay (thin(): run_batched.py --keep-replays, tools/replay_thin.py) is deleted only after its per-game
counts are appended to the batch's PRUNED file, which count() reads in place of a missing replay.
"""
import collections
import json
import os
import re
import sys
import zipfile
from pathlib import Path


LINE = re.compile(rb"OOF (\d+) (.+)")
# The draft's first turn left its precompute unfinished, or play found no usable plan (bots' local_build guards).
HANDOFF = (b"DRAFT-UNFINISHED", b"PLAN-CHECK")


# The draft's first turn cut optional sections to fit (analyse's cap): not a failure, but counted.
CAPPED = b"DRAFT-CAPPED"


def has_line(out, marker):
    return out.startswith(marker) or b"\n" + marker in out


def handoff_failed(out):
    """Whether a bot's stdout has a line starting with one of HANDOFF."""
    return any(has_line(out, m) for m in HANDOFF)


def oof_phases(out):
    """The phase of each `OOF round phase` line (^OOF (\\d+) (.+)$ in the decoded text) not in the draft: found
    with bytes.find, ~3x a regex over a bot's ~600 KB of stdout."""
    hits = []
    i = out.find(b"OOF ")
    while i >= 0:
        if i == 0 or out[i - 1] == 10:
            j = out.find(b"\n", i)
            m = LINE.fullmatch(out, i, len(out) if j < 0 else j)
            if m and not m[2].startswith(b"draft"):
                hits.append(m[2].decode("utf-8", "replace").strip())
        i = out.find(b"OOF ", i + 4)
    return hits


PRUNED = "pruned-stdout.jsonl"


def game_stats(b):
    """One replay's {"stem", "phases": [bot 1's, bot 2's], "handoff": [..], "capped": [..]}."""
    b = Path(b)
    order = b.stem.rsplit("-", 1)[1]  # 12: bot 1 is team A
    stats = {"stem": b.stem, "phases": [[], []], "handoff": [False, False], "capped": [False, False]}
    with zipfile.ZipFile(b) as z:
        for team in "ab":
            bot = 1 if (team == "a") == (order == "12") else 2
            # The engine pads stdout with NULs at line starts, which would hide lines from ^.
            out = z.read(f"team-{team}.stdout").translate(None, b"\0")
            stats["phases"][bot - 1] = oof_phases(out)
            stats["handoff"][bot - 1] = handoff_failed(out)
            stats["capped"][bot - 1] = has_line(out, CAPPED)
    return stats


def thin(d, files):
    """Delete replays `files` of batch d, first appending their game_stats to d/PRUNED (synced before any unlink).
    A replay that is already gone or unreadable is left alone. Returns the number deleted."""
    rows, done = [], []
    for b in map(Path, files):
        try:
            rows.append(json.dumps(game_stats(b), separators=(",", ":")) + "\n")
            done.append(b)
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            continue
    if not done:
        return 0
    fd = os.open(Path(d) / PRUNED, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        size = os.fstat(fd).st_size
        # After a torn write (a full disk), start a fresh line.
        lead = "\n" if size and os.pread(fd, 1, size - 1) != b"\n" else ""
        os.write(fd, (lead + "".join(rows)).encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    for b in done:
        b.unlink(missing_ok=True)
    return len(done)


_pruned = {}


def pruned_rows(path):
    """The rows of a PRUNED file, skipping torn ones."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def pruned(d, stem):
    """game_stats of a thinned replay of batch d, or None; the file is re-read when it has grown."""
    path = Path(d) / PRUNED
    try:
        size = path.stat().st_size
    except OSError:
        return None
    key = str(path)
    if key not in _pruned or _pruned[key][0] != size:
        _pruned[key] = (size, {row["stem"]: row for row in pruned_rows(path)})
    return _pruned[key][1].get(stem)


def count(d, files=None):
    """(bot paths, turns, games, phases, maps, handoffs, capped) for batch d, or for some of its replays; the counters
    are keyed by bot 1 and 2, handoffs counting games with a broken draft handoff, capped those with a capped draft."""
    d = Path(d)
    bots = json.loads((d / "results.json").read_text())["bots"]
    turns, games = collections.Counter(), collections.Counter()
    phases = {1: collections.Counter(), 2: collections.Counter()}
    maps = {1: collections.Counter(), 2: collections.Counter()}
    handoffs, capped = collections.Counter(), collections.Counter()
    if files is None:
        stems = {b.stem for b in d.glob("*.repl26a")}
        if (d / PRUNED).is_file():
            stems |= {row["stem"] for row in pruned_rows(d / PRUNED)}
        files = [d / f"{stem}.repl26a" for stem in sorted(stems)]
    for b in map(Path, files):
        name = b.stem.split("-", 1)[1].rsplit("-", 1)[0]
        try:
            stats = game_stats(b)
        except FileNotFoundError:
            # Thinned, possibly while this ran: thin() records a game before deleting its replay.
            if (stats := pruned(b.parent, b.stem)) is None:
                raise
        for bot in (1, 2):
            hits = stats["phases"][bot - 1]
            handoffs[bot] += stats["handoff"][bot - 1]
            capped[bot] += stats["capped"][bot - 1]
            turns[bot] += len(hits)
            games[bot] += bool(hits)
            for phase in hits:
                phases[bot][phase] += 1
                maps[bot][name] += 1
    return bots, turns, games, phases, maps, handoffs, capped


def main():
    totals = collections.Counter()
    for d in map(Path, sys.argv[1:]):
        bots, turns, games, phases, maps, handoffs, capped = count(d)
        print(f"== {d}")
        for bot in (1, 2):
            totals[bot] += turns[bot]
            print(f"  {Path(bots[bot - 1]).name}: {turns[bot]} out-of-fuel turns in {games[bot]} games;"
                  f" phases {dict(phases[bot].most_common())}; maps {dict(maps[bot].most_common(6))}"
                  + (f"; BROKEN DRAFT HANDOFFS in {handoffs[bot]} games" if handoffs[bot] else "")
                  + (f"; capped drafts in {capped[bot]} games" if capped[bot] else ""))
    if len(sys.argv) > 2:
        print(f"total: bot 1 {totals[1]}, bot 2 {totals[2]}")


if __name__ == "__main__":
    main()
