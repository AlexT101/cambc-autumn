"""Win rates with Wilson 95% intervals by side, pick count, set part, our draft, Fish's draft, map features, and the
loss classes inside each cell.   py research/ideas-2026-11-12/v118-fish-b/breakdown.py"""
import json, math
from collections import defaultdict, Counter
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
F = json.load(open(REPO / "replays/v118b/feat.json"))
CL = {r["key"]: r for r in json.load(open(REPO / "replays/v118b/classes.json"))}


def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def table(title, keyf, minn=8, top=None):
    cells = defaultdict(list)
    for f in F:
        ks = keyf(f)
        for k in (ks if isinstance(ks, list) else [ks]):
            cells[k].append(f)
    print(f"\n### {title}\n\n| cell | games | wins | win % [95% CI] | loss classes |\n|---|---|---|---|---|")
    rows = sorted(cells.items(), key=lambda kv: -len(kv[1]))
    for k, S in rows[:top] if top else rows:
        if len(S) < minn: continue
        w = sum(f["result"] == "win" for f in S); lo, hi = wilson(w, len(S))
        cl = Counter(CL[f["key"]]["class"] for f in S if f["result"] == "loss")
        print(f"| {k} | {len(S)} | {w} | {100 * w / len(S):.0f} [{lo:.0f}-{hi:.0f}] | {', '.join(f'{c} {n}' for c, n in cl.most_common())} |")


fish_lead = lambda f: f["opp_picks"][0]
table("All", lambda f: "all")
table("Side", lambda f: f["side"])
table("Picks a team", lambda f: f["npick"])
table("Set part", lambda f: f["part"])
table("Our draft has Prism", lambda f: "Prism" if "Prism" in f["our_picks"] else "no Prism")
table("Fish's first pick", fish_lead)
table("Fish's draft has", lambda f: [p for p in set(f["opp_picks"])], minn=20)
table("Our draft has", lambda f: [p for p in set(f["our_picks"])], minn=20)
table("Fish has Vesper x we have Prism", lambda f: ("F-Vesper" if "Vesper Vale" in f["opp_picks"] else "F-noVesper") + " / " + ("Prism" if "Prism" in f["our_picks"] else "noPrism"))
table("Fish's draft (8+ games)", lambda f: " / ".join(p.split()[0] for p in f["opp_picks"]))
table("Our draft (8+ games)", lambda f: " / ".join(p.split()[0] for p in f["our_picks"]))
table("Altars on the map", lambda f: f"{f['n_altars']} altar{'s' if f['n_altars'] != 1 else ''}" if f["n_altars"] < 3 else "3+ altars")
table("Map size (longer side)", lambda f: "<=40" if max(f["W"], f["H"]) <= 40 else "41-60" if max(f["W"], f["H"]) <= 60 else "61-80" if max(f["W"], f["H"]) <= 80 else "81+")
table("Game length", lambda f: "<500" if f["rounds"] < 500 else "500-799" if f["rounds"] < 800 else "800-1199" if f["rounds"] < 1200 else "1200+")
# maps: both sides lost / won
bym = defaultdict(list)
for f in F: bym[f["map"]].append(f)
lost_all = sorted(m for m, S in bym.items() if len(S) >= 2 and all(f["result"] == "loss" for f in S))
won_all = sorted(m for m, S in bym.items() if len(S) >= 2 and all(f["result"] == "win" for f in S))
print(f"\n{len(bym)} maps; {len(lost_all)} lost every game ({sum(len(bym[m]) for m in lost_all)} games): {', '.join(lost_all)}")
print(f"{len(won_all)} won every game ({sum(len(bym[m]) for m in won_all)} games)")
