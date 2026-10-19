"""Out-of-fuel play turns per bot in run_batched.py batches (local builds print an `OOF round phase` line for each).

    py tools/fuel/oof.py replays/batch-A replays/batch-B ...
"""
import collections
import json
import re
import sys
import zipfile
from pathlib import Path


def main():
    totals = collections.Counter()
    for d in map(Path, sys.argv[1:]):
        bots = json.loads((d / "results.json").read_text())["bots"]
        turns, games = collections.Counter(), collections.Counter()
        phases = {1: collections.Counter(), 2: collections.Counter()}
        maps = {1: collections.Counter(), 2: collections.Counter()}
        for b in sorted(d.glob("*.repl26a")):
            order = b.stem.rsplit("-", 1)[1]  # 12: bot 1 is team A
            name = b.stem.split("-", 1)[1].rsplit("-", 1)[0]
            with zipfile.ZipFile(b) as z:
                for team in "ab":
                    bot = 1 if (team == "a") == (order == "12") else 2
                    out = z.read(f"team-{team}.stdout").decode("utf-8", "replace")
                    hits = [m for m in re.finditer(r"^OOF (\d+) (.+)$", out, re.M) if not m[2].startswith("draft")]
                    turns[bot] += len(hits)
                    games[bot] += bool(hits)
                    for m in hits:
                        phases[bot][m[2].strip()] += 1
                        maps[bot][name] += 1
        print(f"== {d}")
        for bot in (1, 2):
            totals[bot] += turns[bot]
            print(f"  {Path(bots[bot - 1]).name}: {turns[bot]} out-of-fuel turns in {games[bot]} games;"
                  f" phases {dict(phases[bot].most_common())}; maps {dict(maps[bot].most_common(6))}")
    if len(sys.argv) > 2:
        print(f"total: bot 1 {totals[1]}, bot 2 {totals[2]}")


if __name__ == "__main__":
    main()
