"""SHORTCUT lines per map and kind over batch dirs: py -I shortcuts.py OUT.json batch...

Each game counts both teams (both bots are astraeus builds)."""
import collections
import json
import re
import sys
import zipfile
from pathlib import Path

out_path = Path(sys.argv[1])
per_map = collections.defaultdict(lambda: collections.Counter())
rounds = collections.Counter()
games = collections.Counter()
for d in map(Path, sys.argv[2:]):
    res = json.loads((d / "results.json").read_text())
    for m in res["matches"]:
        rp = Path(m["replay"])
        rp = d / rp.name
        if not rp.exists():
            continue
        name = Path(m["map"]).stem
        key = f"{Path(m['map']).parent.name}/{name}"
        rounds[key] += m["rounds"]
        games[key] += 1
        with zipfile.ZipFile(rp) as z:
            for team in "ab":
                out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                for what in re.findall(r"^SHORTCUT \d+ \d+ (\S+)", out, re.M):
                    per_map[key][what] += 1
json.dump({"maps": {k: dict(v) for k, v in per_map.items()}, "rounds": rounds, "games": games}, out_path.open("w"))
tot = collections.Counter()
for v in per_map.values():
    tot.update(v)
print("total", sum(games.values()), "games", sum(rounds.values()), "rounds")
for k, n in tot.most_common():
    print(f"{k:28s} {n:8d}")
