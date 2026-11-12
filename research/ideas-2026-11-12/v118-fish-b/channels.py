"""Our long tribute channels (100+ gems) and how they end, wins and losses (replay only).

    py research/ideas-2026-11-12/v118-fish-b/channels.py    # -> replays/v118b/channels.json
Per channel: start round, gems, planned turns, whether our score + bag reached the win ("winning"), and its end:
done, or cancelled by lock (an enemy lock placed on that altar), stun, manual (our bot left it), death."""
import json, os, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.environ["CAMBC_ANALYSIS"] = str(REPO / "replays/v118b/analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
from analysis.data import Game  # noqa: E402


def one(f):
    g = Game(f["dir"]); us = 0 if f["side"] == "a" else 1
    R = g.rounds
    out = []; open_ = {}
    locks_them = [e["r"] for e in g.events if e["k"] == "lock_place" and e["team"] != us]
    for e in g.events:
        k = e["k"]
        if k == "tribute_start" and g.team_of[e["a"]] == us and e["gems"] >= 100:
            sc = R["gems"][us][max(0, e["r"] - 2)]
            open_[e["a"]] = {"key": f["key"], "result": f["result"], "r": e["r"], "gems": e["gems"], "dur": e["dur"], "who": g.name_of[e["a"]],
                             "winning": sc + e["gems"] >= 1000, "score": sc, "their": R["gems"][1 - us][max(0, e["r"] - 2)], "altar": e.get("altar")}
        elif k == "tribute_end" and e["a"] in open_:
            c = open_.pop(e["a"]); c.update(end="done", r1=e["r"]); out.append(c)
        elif k == "tribute_cancel" and e["a"] in open_:
            c = open_.pop(e["a"]); c.update(end=e.get("cause", "?"), r1=e["r"], left=e.get("left")); out.append(c)
        elif k == "death" and e["v"] in open_:
            c = open_.pop(e["v"]); c.update(end="death", r1=e["r"]); out.append(c)
    for c in open_.values():
        c.update(end="open", r1=f["rounds"]); out.append(c)
    return {"key": f["key"], "result": f["result"], "channels": out, "locks_them": locks_them, "locks_us": f["locks_us"]}


if __name__ == "__main__":
    F = json.load(open(REPO / "replays/v118b/feat.json"))
    with ProcessPoolExecutor(20) as ex:
        rows = list(ex.map(one, F, chunksize=4))
    json.dump(rows, open(REPO / "replays/v118b/channels.json", "w"))
    ch = [c for r in rows for c in r["channels"]]
    for nm, S in (("all 100+ channels", ch), ("winning-bag channels", [c for c in ch if c["winning"]]), ("300+ channels", [c for c in ch if c["gems"] >= 300])):
        print(f"{nm}: {len(S)}")
        for res in ("win", "loss"):
            T = [c for c in S if c["result"] == res]
            print(f"   in {res}es: {len(T)}  ends {dict(Counter(c['end'] for c in T).most_common())}")
    g = defaultdict(lambda: Counter())
    for r in rows:
        w = [c for c in r["channels"] if c["winning"]]
        if w:
            g[r["result"]]["games with a winning-bag channel"] += 1
            if any(c["end"] == "lock" for c in w): g[r["result"]]["... one cancelled by a lock"] += 1
            if any(c["end"] == "stun" for c in w): g[r["result"]]["... one cancelled by a stun"] += 1
            if any(c["end"] == "manual" for c in w): g[r["result"]]["... one we left ourselves"] += 1
            if any(c["end"] == "death" for c in w): g[r["result"]]["... its carrier died in it"] += 1
            g[r["result"]]["winning channels started"] += len(w)
        g[r["result"]]["games"] += 1
        g[r["result"]]["enemy locks placed"] += len(r["locks_them"]); g[r["result"]]["our locks placed"] += len(r["locks_us"])
    for res in ("win", "loss"):
        print(res, dict(g[res]))
    lost = [r for r in rows if r["result"] == "loss" and any(c["winning"] for c in r["channels"])]
    print("losses with a winning-bag channel started:", len(lost))
    for r in lost:
        w = [c for c in r["channels"] if c["winning"]]
        print("  ", r["key"], "first at r%d bag %d score %d-%d" % (w[0]["r"], w[0]["gems"], w[0]["score"], w[0]["their"]), "ends", dict(Counter(c["end"] for c in w)))
