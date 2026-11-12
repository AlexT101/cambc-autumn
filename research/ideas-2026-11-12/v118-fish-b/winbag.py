"""Games in which one of our champions held the winning bag (our tributes + its bag >= 1000), and what became of it.

    py research/ideas-2026-11-12/v118-fish-b/winbag.py     # -> replays/v118b/winbag.json
first: the first round it held; held: rounds it stayed winning; then per game the channels started on it and their ends,
the enemy locks placed while it was held, and the end (won at round, or the carrier died with it, or the game ended first)."""
import json, os, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.environ["CAMBC_ANALYSIS"] = str(REPO / "replays/v118b/analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
from analysis.data import Game  # noqa: E402


def one(f):
    g = Game(f["dir"]); us = 0 if f["side"] == "a" else 1
    R = g.rounds; ch = R["champions"]; n = len(R["round"])
    first = None; held = 0; who = None
    for i in range(n):
        s = R["gems"][us][i]
        best = max(((ch[g.idx[c]]["gems"][i], c) for c in g.team_ids[us]), default=(0, None))
        if s < 1000 and s + best[0] >= 1000:
            held += 1
            if first is None:
                first = i + 1; who = best[1]; bag0 = best[0]; s0 = s; e0 = R["gems"][1 - us][i]
    if first is None:
        return {"key": f["key"], "result": f["result"], "first": None}
    locks = sum(1 for e in g.events if e["k"] == "lock_place" and e["team"] != us and e["r"] >= first)
    died = [(e["r"], e["gems"], g.name_of.get(e.get("by"), "camp")) for e in g.deaths if e["v"] == who and e["r"] >= first and e["gems"] >= 100]
    a = ch[g.idx[who]]
    return {"key": f["key"], "result": f["result"], "first": first, "held": held, "who": g.name_of[who], "bag0": bag0, "score0": s0, "their0": e0,
            "rounds": n, "locks_after": locks, "died": died, "their_end": f["opp_gems"], "hp0": round(a["hp"][first - 1] / a["maxHp"][first - 1], 2),
            "maxhp": round(a["maxHp"][first - 1]), "altars": len(g.map.altars)}


if __name__ == "__main__":
    F = json.load(open(REPO / "replays/v118b/feat.json"))
    with ProcessPoolExecutor(20) as ex:
        rows = list(ex.map(one, F, chunksize=4))
    json.dump(rows, open(REPO / "replays/v118b/winbag.json", "w"))
    H = [r for r in rows if r["first"]]
    W = [r for r in H if r["result"] == "win"]; L = [r for r in H if r["result"] == "loss"]
    import statistics as st
    print(f"{len(H)} games reached a winning bag: {len(W)} won, {len(L)} lost ({100 * len(W) / len(H):.0f}% converted); wins without ever holding one: {sum(1 for r in rows if not r['first'] and r['result'] == 'win')}")
    print(f"  wins: first held r{st.median(r['first'] for r in W):.0f} (median), rounds from first holding it to the win: median {st.median(r['rounds'] - r['first'] for r in W):.0f}, q3 {st.quantiles([r['rounds'] - r['first'] for r in W], n=4)[2]:.0f}, max {max(r['rounds'] - r['first'] for r in W)}; bag median {st.median(r['bag0'] for r in W):.0f}")
    print(f"  losses: first held r{st.median(r['first'] for r in L):.0f}, held for a median {st.median(r['held'] for r in L):.0f} rounds; carrier died with 100+ after in {sum(1 for r in L if r['died'])}")
    for r in sorted(L, key=lambda r: r["first"]):
        print(f"   {r['key']} {r['who']} first r{r['first']} bag {r['bag0']} score {r['score0']}-{r['their0']} held {r['held']} rounds, game ended r{r['rounds']} (they {r['their_end']}); enemy locks after {r['locks_after']}; died {r['died']}; altars {r['altars']}")
