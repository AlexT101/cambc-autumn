"""Out-of-fuel play turns per bot in run_batched.py batches (local builds print an `OOF round phase` line for each),
and broken draft handoffs: local builds resign on one, printing a line starting with one of HANDOFF.

    py tools/fuel/oof.py replays/batch-A replays/batch-B ...
"""
import collections
import json
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


def count(d, files=None):
    """(bot paths, turns, games, phases, maps, handoffs, capped) for batch d, or for some of its replays; the counters
    are keyed by bot 1 and 2, handoffs counting games with a broken draft handoff, capped those with a capped draft."""
    d = Path(d)
    bots = json.loads((d / "results.json").read_text())["bots"]
    turns, games = collections.Counter(), collections.Counter()
    phases = {1: collections.Counter(), 2: collections.Counter()}
    maps = {1: collections.Counter(), 2: collections.Counter()}
    handoffs, capped = collections.Counter(), collections.Counter()
    for b in sorted(d.glob("*.repl26a")) if files is None else map(Path, files):
        order = b.stem.rsplit("-", 1)[1]  # 12: bot 1 is team A
        name = b.stem.split("-", 1)[1].rsplit("-", 1)[0]
        with zipfile.ZipFile(b) as z:
            for team in "ab":
                bot = 1 if (team == "a") == (order == "12") else 2
                # The engine pads stdout with NULs at line starts, which would hide lines from ^.
                out = z.read(f"team-{team}.stdout").translate(None, b"\0")
                hits = oof_phases(out)
                handoffs[bot] += handoff_failed(out)
                capped[bot] += has_line(out, CAPPED)
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
