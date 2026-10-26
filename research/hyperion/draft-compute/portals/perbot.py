"""Routing shortcuts per bot (0 CAND, 1 REF) and stalled champion-games, per map: py -I perbot.py batch..."""
import collections, json, re, sys, zipfile
from pathlib import Path

kinds = {"crow-flies-farm", "static-descend", "farm-no-route", "farm-kept-target", "siege-route-fuel"}
tot = [collections.Counter(), collections.Counter()]
stalls = [0, 0]
rounds = []
for d in map(Path, sys.argv[1:]):
    res = json.loads((d / "results.json").read_text())
    for m in res["matches"]:
        rounds.append(m["rounds"])
        rp = d / Path(m["replay"]).name
        with zipfile.ZipFile(rp) as z:
            for team in "ab":
                bot = m["order"][0 if team == "a" else 1]
                out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                c = collections.Counter()
                for champ, what in re.findall(r"^SHORTCUT \d+ (\d+) (\S+)", out, re.M):
                    if what in kinds:
                        tot[bot][what] += 1
                        c[champ] += 1
                big = [n for n in c.values() if n >= 300]
                stalls[bot] += len(big)
                if big:
                    print(Path(m["map"]).stem, "bot", bot, "team", team, "stalled champions", big, "winner", m["winner"], "rounds", m["rounds"])
for b in (0, 1):
    print("bot", b, dict(tot[b]), "sum", sum(tot[b].values()), "stalled champion-games", stalls[b])
rounds.sort()
print("games", len(rounds), "median rounds", rounds[len(rounds) // 2], "min", rounds[0], "max", rounds[-1])
