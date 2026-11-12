"""Turn-level dump of a round window from the extract: every action of the listed champions (default: all), with health.

    py research/ideas-2026-11-12/v118-fish-b/ep.py KEY R0 R1 [--ids 3,5] [--trace NAME]
--trace NAME adds our trace lines (replays/v118b/runs/NAME/KEY/trace.stdout.gz) of those rounds."""
import argparse, gzip, json, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.environ["CAMBC_ANALYSIS"] = str(REPO / "replays/v118b/analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
from analysis.data import Game  # noqa: E402
ap = argparse.ArgumentParser()
ap.add_argument("key"); ap.add_argument("r0", type=int); ap.add_argument("r1", type=int)
ap.add_argument("--ids"); ap.add_argument("--trace")
a = ap.parse_args()
F = {f["key"]: f for f in json.load(open(REPO / "replays/v118b/feat.json"))}
f = F[a.key]; g = Game(f["dir"]); us = 0 if f["side"] == "a" else 1
ids = [int(x) for x in a.ids.split(",")] if a.ids else [c["id"] for c in g.champs]
T = lambda c: ("U:" if g.team_of[c] == us else "T:") + g.name_of[c][:5] + f"#{c}"
ch = g.rounds["champions"]
tr = {}
if a.trace:
    p = REPO / f"replays/v118b/runs/{a.trace}/{a.key}/trace.stdout.gz"
    tt = json.load(open(p.parent / "direct.json"))["ladder_trusted_through"]
    print(f"trace {a.trace}: trusted through r{tt} of {f['rounds']}")
    for line in gzip.open(p, "rt", errors="replace"):
        w = line.split()
        if len(w) > 2 and w[1].lstrip("-").isdigit() and a.r0 <= int(w[1]) <= a.r1:
            tr.setdefault(int(w[1]), []).append(line.rstrip()[:260])
print(f"{a.key} {f['map']} side {f['side']} {f['result']}  us: {', '.join(T(c) for c in g.team_ids[us])} | them: {', '.join(T(c) for c in g.team_ids[1-us])}")
cur = None
for e in g.events:
    r = e["r"]
    if r < a.r0 or r > a.r1:
        continue
    if r != cur:
        cur = r
        st = "  ".join(f"{T(c)} {ch[g.idx[c]]['x'][max(0,r-2)]},{ch[g.idx[c]]['y'][max(0,r-2)]} hp{round(ch[g.idx[c]]['hp'][max(0,r-2)])}/{round(ch[g.idx[c]]['maxHp'][max(0,r-2)])} g{ch[g.idx[c]]['gems'][max(0,r-2)]}" for c in ids if ch[g.idx[c]]["alive"][max(0, r - 2)])
        print(f"--- r{r} start: {st}   score {g.rounds['gems'][us][max(0,r-2)]}-{g.rounds['gems'][1-us][max(0,r-2)]}")
        for l in tr.get(r - 1, []):
            pass
    k = e["k"]
    who = e.get("a", e.get("v"))
    if k in ("camp_attack",):
        if e.get("tgt") in ids: print(f"      camp{e['camp']} hits {T(e['tgt'])} {round(e['dmg'])}")
        continue
    if who is None or who not in ids and not (e.get("tgt") in ids) and not any(x[0] in ids for x in e.get("dmg", [])):
        continue
    if k in ("recall_start", "recall_cancel", "ward", "shop"):
        continue
    desc = k
    if k == "move": desc = f"move {e['f']}->{e['to']}"
    elif k in ("attack", "cast"):
        tg = T(e["tgt"]) if e.get("tgt") is not None else (f"camp{e['camp']}" if e.get("camp") is not None else str(e.get("to")))
        desc = f"{k}{'/' + e['ab'] if k == 'cast' else ''} -> {tg} dmg {[(T(x[0]), round(x[1])) for x in e.get('dmg', [])]}{' STUN ' + str([T(x) for x in e['stun']]) if e.get('stun') else ''}{' moved ' + str(e['moved']) if e.get('moved') else ''}{' heal ' + str(e['heal']) if e.get('heal') else ''}"
    elif k == "death": desc = f"DEATH bag {e['gems']} by {T(e['by']) if 'by' in e else 'camp'}"
    elif k in ("tribute_start", "tribute_end", "tribute_cancel"): desc = f"{k} {e.get('gems')} {e.get('cause', '')}"
    print(f"   t{e['t']:2} {T(who)}: {desc}")
    if k in ("move", "attack", "cast") and a.trace and e.get("a") in ids:
        pass
if a.trace:
    print("TRACE")
    for r in sorted(tr):
        for l in tr[r]: print("  ", l)
