"""What the bot's retreat test and stand verdict said before our Prism's hoard deaths (trace run v: D, DX, CS + want_home's
reason), on the games and rounds that reproduce the live game (ladder_trusted_through).

    py research/ideas-2026-11-12/v118-fish-b/verdicts.py [--show N]
For each Prism death with 100+ gems whose round is trusted: per turn of the last 14 rounds the branch, want_home's reason
(0 asked and no; 1 recall line / pack zone; 2 camps; 3 camp fled; 5 finish_heal; 6 stand lost; -1 not asked), the stand
verdict CS (lost, self_falls, turns to kill us / them, margin) and whether the killer was in sight."""
import argparse, json, os, sys
from collections import Counter, defaultdict
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dlib  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--show", type=int, default=0); ap.add_argument("--run", default="v")
a = ap.parse_args()
D = json.load(open(REPO / "replays/v118b/deathctx.json"))
F = {f["key"]: f for f in json.load(open(REPO / "replays/v118b/feat.json"))}
RT = {(d["key"], d["r"], d["v"]): d for d in json.load(open(REPO / "replays/v118b/retreats.json"))}
P = [d for d in D if d["v"] == "Prism" and d["bag"] >= 100]
val = dlib.validation(a.run)
tot = len(P); ok = [d for d in P if (val.get(d["key"], {}).get("ladder_trusted_through") or 0) >= d["r"]]
print(f"{tot} Prism deaths with 100+ gems; {len(ok)} in rounds the trace run '{a.run}' reproduces")
cache = {}


def load(key):
    if key not in cache:
        dx, cs, br = {}, defaultdict(list), {}
        for w in dlib.lines(a.run, key, {"D", "DX", "CS"}):
            try:
                if w[0] == "D": br[(int(w[1]), int(w[2]))] = w[3]
                elif w[0] == "DX": dx[(int(w[1]), int(w[2]))] = [int(x) for x in w[3:]]
                elif w[0] == "CS": cs[(int(w[1]), int(w[2]))].append(w)
            except ValueError:
                pass
        cache[key] = (dx, cs, br)
    return cache[key]


first_R = Counter(); pre_tw = Counter(); pre_cs = Counter(); rows = []
for d in ok:
    f = F[d["key"]]; pid = [c["id"] for c in f["champs"] if c["us"] and c["type"] == "Prism"][0]
    dx, cs, br = load(d["key"])
    rt = RT[(d["key"], d["r"], "Prism")]
    r_start = d["r"] - rt["streak"]          # first round of the final retreat streak (== death round if none)
    # the reason on the first retreat turn
    x = dx.get((r_start, pid))
    if rt["streak"] >= 1 and x:
        first_R[x[12]] += 1
    # the last turn before the streak: was want_home asked, what did the stand verdict say
    y = dx.get((r_start - 1, pid))
    if y:
        pre_tw[y[12]] += 1
    c = cs.get((r_start - 1, pid))
    if c:
        w = c[-1]; lost, falls_self = int(w[10]), int(w[11]); pre_cs[("lost" if lost else "falls" if falls_self else "ok")] += 1
    else:
        pre_cs["no roster"] += 1
    line = []
    for r in range(d["r"] - 14, d["r"] + 1):
        z = dx.get((r, pid)); c = cs.get((r, pid))
        s = br.get((r, pid), "?")
        if z: s += f"{z[12]}" if z[12] >= 0 else "."
        if c:
            w = c[-1]; s += "L" if int(w[10]) else ("f" if int(w[11]) else "w"); s += f"({w[12]}/{w[13]})"
        line.append(s)
    rows.append((d, rt, " ".join(line)))
print("want_home's reason on the first turn of the final retreat streak:", dict(first_R), "(1 recall line or pack zone, 6 stand lost, 5 finish_heal, 2/3 camps)")
print("on the turn before that streak (or before the death): want_home", dict(pre_tw), "(0 = asked, said stay; -1 = not asked: a channel or an early branch)")
print("   the stand verdict then:", dict(pre_cs), "(ok = a roster formed and the stand was judged won without our fall)")
for d, rt, line in sorted(rows, key=lambda x: -x[0]["bag"])[: a.show]:
    print(f"{d['key']} r{d['r']} bag {d['bag']} by {d['by'][:6]} first hit r{d['r0']} streak {rt['streak']} d_start {rt['d_start']} hits {rt['hits']}\n    {line}")
