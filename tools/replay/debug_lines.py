"""Debug lines per bot in run_batched.py batches: stdout lines starting with each prefix (local builds print
debug_block output into each bundle's team-<x>.stdout).

    py tools/replay/debug_lines.py SRCH-PASS SRCH-STRANDED -- replays/batch-A replays/batch-B ...
    py tools/replay/debug_lines.py SRCH-STRANDED --show 20 -- replays/batch-A    # also print the first 20 lines
"""
import argparse
import collections
import json
import re
import sys
import zipfile
from pathlib import Path


def main():
    argv = sys.argv[1:]
    if "--" not in argv:
        sys.exit(__doc__)
    split = argv.index("--")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("prefixes", nargs="+")
    p.add_argument("--show", type=int, default=0, help="print up to N matching lines, with their game")
    args = p.parse_args(argv[:split])
    args.batches = argv[split + 1:]
    counts = collections.Counter()
    games = collections.Counter()
    shown = 0
    names = {}
    for d in map(Path, args.batches):
        bots = json.loads((d / "results.json").read_text())["bots"]
        for b in sorted(d.glob("*.repl26a")):
            order = b.stem.rsplit("-", 1)[1]  # 12: bot 1 is team A
            with zipfile.ZipFile(b) as z:
                for team in "ab":
                    bot = Path(bots[0 if (team == "a") == (order == "12") else 1]).name
                    names[bot] = True
                    # The engine pads stdout with NULs at line starts, which would hide lines from ^.
                    out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                    for prefix in args.prefixes:
                        hits = re.findall(rf"^{re.escape(prefix)}\b.*$", out, re.M)
                        counts[bot, prefix] += len(hits)
                        games[bot, prefix] += bool(hits)
                        for line in hits:
                            if shown < args.show:
                                print(f"{b.name} {team}: {line}")
                                shown += 1
    for bot in names:
        print(bot + ": " + ", ".join(f"{prefix} {counts[bot, prefix]} in {games[bot, prefix]} games" for prefix in args.prefixes))


if __name__ == "__main__":
    main()
