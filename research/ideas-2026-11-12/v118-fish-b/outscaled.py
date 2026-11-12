"""When does a Fish champion become a K-hit killer of our Prism, as our Prism itself could know it (replay only)?

    py research/ideas-2026-11-12/v118-fish-b/outscaled.py

For every Prism game: each round, hits = Prism max health / the largest Strength the Prism has seen on a living enemy
champion (Strength is readable on a visible champion; the last sighting is kept). The trigger round t(K) is the first
round with a bag of BAG+ gems and hits < K. Reported for K = 3..8: games where it fires, in wins and losses; in the
HOARD-KILL losses how many rounds before the hoard death it fired and the bag then; in wins how many rounds before the end."""
import json, os, sys, statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.environ["CAMBC_ANALYSIS"] = str(REPO / "replays/v118b/analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
from analysis.data import Game  # noqa: E402
BAG = 100
KS = (3, 4, 5, 6, 8, 10)


def one(f):
    if "Prism" not in f["our_picks"]:
        return None
    g = Game(f["dir"]); us = 0 if f["side"] == "a" else 1
    R = g.rounds; ch = R["champions"]; n = len(R["round"])
    p = [c["id"] for c in g.champs if c["team"] == us and c["name"] == "Prism"][0]
    a = ch[g.idx[p]]
    seen = {}
    trig = {}
    series = []
    for i in range(n):
        for e in a["sees"][i]:
            seen[e] = ch[g.idx[e]]["str"][i]
        top = max(seen.values(), default=0)
        hits = a["maxHp"][i] / top if top > 0 else 99
        series.append(hits)
        for K in KS:
            if K not in trig and a["alive"][i] and a["gems"][i] >= BAG and hits < K:
                trig[K] = (i + 1, a["gems"][i], R["gems"][us][i], R["gems"][1 - us][i])
    deaths = [(e["r"], e["gems"]) for e in g.deaths if e["v"] == p and e["gems"] >= BAG and "by" in e]
    return {"key": f["key"], "result": f["result"], "rounds": n, "trig": trig, "deaths": deaths,
            "hits_cp": [round(series[min(n, r) - 1], 1) for r in (200, 300, 400, 500, 600, 700, 800)]}


if __name__ == "__main__":
    F = json.load(open(REPO / "replays/v118b/feat.json"))
    cls = {r["key"]: r["class"] for r in json.load(open(REPO / "replays/v118b/classes.json"))}
    with ProcessPoolExecutor(20) as ex:
        rows = [r for r in ex.map(one, F, chunksize=4) if r]
    json.dump(rows, open(REPO / "replays/v118b/outscaled.json", "w"))
    W = [r for r in rows if r["result"] == "win"]; L = [r for r in rows if r["result"] == "loss"]
    HK = [r for r in L if cls[r["key"]] == "HOARD-KILL"]
    print(f"{len(rows)} Prism games: {len(W)} wins, {len(L)} losses ({len(HK)} HOARD-KILL)")
    print("median hits-to-kill (Prism max HP / largest enemy Strength it has seen) at r200..r800:")
    for nm, S in (("wins", W), ("losses", L), ("HOARD-KILL", HK)):
        print(f"  {nm:10}", [round(st.median(r["hits_cp"][i] for r in S if r["rounds"] >= rr), 1) for i, rr in enumerate((200, 300, 400, 500, 600, 700, 800)) if any(r["rounds"] >= rr for r in S)])
    for K in KS:
        fw = [r for r in W if str(K) in r["trig"] or K in r["trig"]]; fl = [r for r in L if K in r["trig"]]; fh = [r for r in HK if K in r["trig"]]
        lead = []
        covered = 0
        for r in fh:
            if not r["deaths"]:
                continue
            d = min(r["deaths"])
            if r["trig"][K][0] < d[0]:
                covered += 1; lead.append(d[0] - r["trig"][K][0])
        wl = [r["rounds"] - r["trig"][K][0] for r in fw]
        print(f"K={K}: fires in {len(fw)}/{len(W)} wins ({100 * len(fw) / len(W):.0f}%), {len(fl)}/{len(L)} losses; before the first 100+ hoard death in {covered}/{len(HK)} HOARD-KILL losses"
              f" (median {st.median(lead) if lead else 0:.0f} rounds before, q1 {st.quantiles(lead, n=4)[0] if len(lead) > 3 else 0:.0f});"
              f" in wins it fires a median {st.median(wl) if wl else 0:.0f} rounds before the end, bag then median {st.median([r['trig'][K][1] for r in fw]) if fw else 0:.0f}")
