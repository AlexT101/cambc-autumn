"""One game's timeline in our frame, from the extract: every STEP rounds the tributed and carried gems, earned gold and
the largest bag of each team, then the interval's deaths (victim, bag, killer, place), tributes and locks.

    py research/ideas-2026-11-12/v118-fish-b/tl.py KEY [--step 50] [--from R --to R]"""
import argparse, json, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.environ["CAMBC_ANALYSIS"] = str(REPO / "replays/v118b/analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
from analysis.data import Game  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("key"); ap.add_argument("--step", type=int, default=50)
ap.add_argument("--from", dest="lo", type=int, default=1); ap.add_argument("--to", dest="hi", type=int, default=9999)
a = ap.parse_args()
F = {f["key"]: f for f in json.load(open(REPO / "replays/v118b/feat.json"))}
f = F[a.key]
g = Game(f["dir"])
us = 0 if f["side"] == "a" else 1
R = g.rounds; ch = R["champions"]; n = len(R["round"])
ids = {t: [c["id"] for c in g.champs if c["team"] == t] for t in (0, 1)}
T = lambda c: g.name_of[c][:5] + f"#{c}"
print(f"{a.key} {f['map']} side {f['side']} {f['result']} {f['our_gems']}-{f['opp_gems']} r{f['rounds']} {f['end']}  {g.map.W}x{g.map.H} altars {g.map.altars}")
print("  us:  ", ", ".join(T(c) for c in ids[us])); print("  them:", ", ".join(T(c) for c in ids[1 - us]))
ev = [e for e in g.events if e["k"] in ("death", "tribute_end", "tribute_start", "tribute_cancel", "lock_place", "lock_destroyed", "tribute_blocked", "capture")]
i = 0
for r in list(range(a.step, n, a.step)) + [n]:
    if r < a.lo or r - a.step > a.hi: 
        while i < len(ev) and ev[i]["r"] <= r: i += 1
        continue
    row = []
    for t in (us, 1 - us):
        car = [(ch[g.idx[c]]["gems"][r - 1], c) for c in ids[t]]
        gold = sum(ch[g.idx[c]]["earned"][r - 1] for c in ids[t])
        big = max(car)
        row.append(f"trib {R['gems'][t][r-1]:4} car {sum(x for x, _ in car):4} (max {T(big[1])} {big[0]:3}) gold {gold:5}")
    print(f"r{r:4} US {row[0]} | THEM {row[1]}")
    caps = {us: [0, 0], 1 - us: [0, 0]}
    while i < len(ev) and ev[i]["r"] <= r:
        e = ev[i]; i += 1; k = e["k"]
        if k == "capture":
            caps[e["team"]][0] += sum(s[1] for s in e["shares"]); caps[e["team"]][1] += 1
            grp = g.map.groups[e["g"]]
            if "Monolith" in grp["types"]:
                print(f"      r{e['r']} MONOLITH captured by {'US' if e['team'] == us else 'THEM'} {e['shares']}")
        elif k == "death":
            who = "US  " if g.team_of[e["v"]] == us else "THEM"
            by = T(e["by"]) if "by" in e else f"camp{e.get('camp')}"
            own = g.map.own(g.team_of[e["v"]], tuple(e["at"])); h = {0: "own", 1: "enemy", -1: "mid"}[g.map.half(own)]
            print(f"      r{e['r']} DEATH {who} {T(e['v'])} bag {e['gems']} by {by} at {e['at']} ({h} half, altar {g.map.altar_dist(tuple(e['at']))}){' linked' if e.get('linked') is not None else ''}")
        elif k == "tribute_end":
            print(f"      r{e['r']} tribute {'US  ' if g.team_of[e['a']] == us else 'THEM'} {T(e['a'])} {e['gems']} -> {e['total']}")
        elif k == "tribute_start" and e["gems"] >= 100:
            print(f"      r{e['r']} tribute START {'US  ' if g.team_of[e['a']] == us else 'THEM'} {T(e['a'])} {e['gems']} dur {e['dur']}")
        elif k == "tribute_cancel" and e["gems"] >= 30:
            print(f"      r{e['r']} tribute CANCEL {'US  ' if g.team_of[e['a']] == us else 'THEM'} {T(e['a'])} {e['gems']} cause {e.get('cause')} left {e.get('left')}")
        elif k in ("lock_place", "tribute_blocked"):
            print(f"      r{e['r']} {k} {'US' if (e.get('team', g.team_of.get(e.get('a'))) == us) else 'THEM'} {e.get('to') or e.get('altar')}")
