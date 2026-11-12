"""Retreat streaks before our deaths: exact D branches (runs/d) joined with replay positions.

    py research/ideas-2026-11-12/v118-fish-b/retreats.py     # -> replays/v118b/retreats.json
For each death of ours to a champion: the streak of consecutive retreat turns ('R', also the mixed R/B/T/K/t/k/r/H turns of a
bag carrier heading home) that ends at the death; at the streak's first turn: distance to the eventual killer, whether
the victim saw it, health share, steps of walk to our spawn (Chebyshev lower bound), the killer's Strength and
hits-to-kill; over the streak: tiles the victim moved, and the distance to the killer each round."""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.environ["CAMBC_ANALYSIS"] = str(REPO / "replays/v118b/analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis.data import Game, chebyshev  # noqa: E402
import dlib  # noqa: E402
HOME = set("RBTKtkrHW")


def one(f):
    g = Game(f["dir"]); us = 0 if f["side"] == "a" else 1
    R = g.rounds; ch = R["champions"]; n = len(R["round"])
    b = dlib.branches("d", f["key"])
    sc = g.map.spawn_center(us)
    out = []
    for e in g.deaths:
        v = e["v"]
        if g.team_of[v] != us or "by" not in e or e.get("linked") is not None:
            continue
        k = e["by"]; r = e["r"]
        a = ch[g.idx[v]]; kk = ch[g.idx[k]]
        # walk back over the victim's turns before the death round
        s = r - 1
        while s >= 1 and b.get((s, v), "?") == "R":
            s -= 1
        r_start = s + 1  # first round of the pure R streak (may be r if none)
        streak = r - r_start
        s2 = r - 1
        while s2 >= 1 and b.get((s2, v), "?") in HOME:
            s2 -= 1
        home_streak = r - 1 - s2
        i0 = max(0, r_start - 2)
        vp, kp = g.pos(v, i0), g.pos(k, i0)
        dists = []
        for rr in range(r_start, r):
            p1, p2 = g.pos(v, rr - 1), g.pos(k, rr - 1)
            dists.append(chebyshev(p1, p2) if p1 and p2 else None)
        moved = 0
        for rr in range(r_start, r):
            p0, p1 = g.pos(v, max(0, rr - 2)), g.pos(v, rr - 1)
            if p0 and p1 and p0 != p1: moved += 1
        out.append({"key": f["key"], "result": f["result"], "r": r, "v": g.name_of[v], "by": g.name_of[k], "bag": e["gems"],
                    "branch_last": b.get((r - 1, v), "?"), "streak": streak, "home_streak": home_streak,
                    "d_start": chebyshev(vp, kp) if vp and kp else None, "saw": k in a["sees"][i0], "hp_start": round(a["hp"][i0] / a["maxHp"][i0], 2),
                    "home_dist": round(chebyshev(vp, sc)) if vp else None, "hits": round(a["hp"][i0] / max(1, kk["str"][i0]), 1),
                    "kstr": round(kk["str"][i0]), "maxhp": round(a["maxHp"][i0]), "moved": moved, "dists": dists})
    return out


if __name__ == "__main__":
    F = json.load(open(REPO / "replays/v118b/feat.json"))
    with ProcessPoolExecutor(20) as ex:
        rows = [d for ds in ex.map(one, F, chunksize=4) for d in ds]
    json.dump(rows, open(REPO / "replays/v118b/retreats.json", "w"))
    import statistics as st
    from collections import Counter
    def show(nm, S):
        Rr = [d for d in S if d["streak"] >= 1]
        print(f"{nm}: {len(S)} deaths; died on a retreat streak {len(Rr)} ({100 * len(Rr) // max(1, len(S))}%)")
        if not Rr: return
        print(f"   streak length: median {st.median(d['streak'] for d in Rr)}, quartiles {st.quantiles([d['streak'] for d in Rr], n=4)}; 5+ rounds: {sum(d['streak'] >= 5 for d in Rr)}, 10+: {sum(d['streak'] >= 10 for d in Rr)}")
        ds = [d['d_start'] for d in Rr if d['d_start'] is not None]
        print(f"   at the streak's start: distance to the killer {sorted(Counter(min(x, 9) for x in ds).items())} (9 = 9+); saw it {sum(d['saw'] for d in Rr)}; health share median {st.median(d['hp_start'] for d in Rr)}; >=0.8: {sum(d['hp_start'] >= 0.8 for d in Rr)}, <0.5: {sum(d['hp_start'] < 0.5 for d in Rr)}; hits-to-kill median {st.median(d['hits'] for d in Rr)}; home {st.median(d['home_dist'] for d in Rr if d['home_dist'] is not None)} tiles away")
        print(f"   moved on {100 * sum(d['moved'] for d in Rr) // max(1, sum(d['streak'] for d in Rr))}% of the streak's rounds")
    P = [d for d in rows if d["v"] == "Prism" and d["bag"] >= 100]
    show("Prism, 100+ bag", P)
    show("Prism, 100+ bag, killed by Vesper", [d for d in P if d["by"] == "Vesper Vale"])
    show("all deaths", rows)
    show("deaths to Vesper, any victim", [d for d in rows if d["by"] == "Vesper Vale"])
