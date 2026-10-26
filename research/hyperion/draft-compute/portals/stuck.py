"""Champions with many routing shortcuts in one game: py -I stuck.py MIN batch..."""
import collections, json, re, sys, zipfile
from pathlib import Path

kinds = {"crow-flies-farm", "static-descend", "farm-no-route", "farm-kept-target", "siege-route-fuel"}
lim = int(sys.argv[1])
per = collections.Counter()
hist = collections.Counter()
games_with = set()
for d in map(Path, sys.argv[2:]):
    res = json.loads((d / "results.json").read_text())
    for m in res["matches"]:
        rp = d / Path(m["replay"]).name
        with zipfile.ZipFile(rp) as z:
            for team in "ab":
                out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                c = collections.Counter()
                for champ, what in re.findall(r"^SHORTCUT \d+ (\d+) (\S+)", out, re.M):
                    if what in kinds:
                        c[champ, what] += 1
                for (champ, what), n in c.items():
                    hist[min(n // 50 * 50, 500)] += 1
                    if n >= lim:
                        print(Path(m["map"]).stem, rp.name[-7:-8], team, champ, what, n, "rounds", m["rounds"], "winner", m["winner"], m["order"])
                        games_with.add(rp.name)
print("histogram of per-champion-game counts (bucket 50):", sorted(hist.items()))
print("games with a champion over", lim, len(games_with))
