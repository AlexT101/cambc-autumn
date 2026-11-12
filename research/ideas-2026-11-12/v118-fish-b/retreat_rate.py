"""Every retreat streak of ours (exact D branches), not only the fatal ones: how often a retreat from a near enemy ends in death.

    py research/ideas-2026-11-12/v118-fish-b/retreat_rate.py
A streak is a run of consecutive 'R' turns of one champion, alive and off its spawn at the start, with an enemy champion
within 6 at the start. It fails when the champion dies to a champion in the streak or the round after it. By nearest
enemy's type, by hits-to-kill (our health / that enemy's Strength), by our type, by distance at the start, by result."""
import json, os, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.environ["CAMBC_ANALYSIS"] = str(REPO / "replays/v118b/analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis.data import Game, chebyshev  # noqa: E402
import dlib  # noqa: E402


def one(f):
    g = Game(f["dir"]); us = 0 if f["side"] == "a" else 1
    R = g.rounds; ch = R["champions"]; n = len(R["round"])
    b = dlib.branches("d", f["key"])
    deaths = {(e["v"], e["r"]): e for e in g.deaths if "by" in e}
    out = []
    for v in g.team_ids[us]:
        a = ch[g.idx[v]]
        r = 1
        while r <= n:
            if b.get((r, v)) != "R" or not a["alive"][max(0, r - 2)]:
                r += 1; continue
            r0 = r
            while r <= n and b.get((r, v)) == "R":
                r += 1
            r1 = r - 1
            i0 = max(0, r0 - 2)
            vp = g.pos(v, i0)
            if not vp or g.map.in_spawn(us, vp):
                continue
            near = [(chebyshev(vp, g.pos(e, i0)), e) for e in g.team_ids[1 - us] if g.pos(e, i0)]
            near = [x for x in near if x[0] <= 6]
            if not near:
                continue
            d, e = min(near)
            died = next((deaths[(v, rr)] for rr in range(r0, r1 + 2) if (v, rr) in deaths), None)
            es = ch[g.idx[e]]["str"][i0]
            out.append({"res": f["result"], "v": g.name_of[v], "near": g.name_of[e], "d": d, "len": r1 - r0 + 1, "died": died is not None,
                        "bag": a["gems"][i0], "hp": round(a["hp"][i0] / a["maxHp"][i0], 2), "hits": a["hp"][i0] / max(1, es), "n_near": len(near),
                        "allies6": sum(1 for c in g.team_ids[us] if c != v and g.pos(c, i0) and chebyshev(g.pos(c, i0), vp) <= 6), "r": r0})
    return out


if __name__ == "__main__":
    F = json.load(open(REPO / "replays/v118b/feat.json"))
    with ProcessPoolExecutor(20) as ex:
        S = [d for ds in ex.map(one, F, chunksize=4) for d in ds]
    json.dump(S, open(REPO / "replays/v118b/retreat_rate.json", "w"))
    def tab(title, key, order=None, minn=30):
        c = defaultdict(lambda: [0, 0])
        for s in S:
            k = key(s)
            if k is None: continue
            c[k][0] += 1; c[k][1] += s["died"]
        print(title)
        for k in (order or sorted(c, key=lambda k: -c[k][0])):
            if k in c and c[k][0] >= minn:
                print(f"   {str(k):16} streaks {c[k][0]:5}  died {c[k][1]:4} = {100 * c[k][1] / c[k][0]:4.1f}%")
    print(len(S), "retreat streaks with an enemy within 6 at the start;", sum(s["died"] for s in S), f"end in death ({100 * sum(s['died'] for s in S) / len(S):.1f}%)")
    tab("by the nearest enemy's type", lambda s: s["near"])
    hb = lambda h: "<2" if h < 2 else "2-3" if h < 3 else "3-4" if h < 4 else "4-6" if h < 6 else "6-10" if h < 10 else "10+"
    tab("by hits-to-kill (our health / the nearest enemy's Strength)", lambda s: hb(s["hits"]), ["<2", "2-3", "3-4", "4-6", "6-10", "10+"])
    tab("nearest is Vesper, by hits-to-kill", lambda s: hb(s["hits"]) if s["near"] == "Vesper Vale" else None, ["<2", "2-3", "3-4", "4-6", "6-10", "10+"], 10)
    tab("by our champion", lambda s: s["v"])
    tab("by distance at the start", lambda s: s["d"], [1, 2, 3, 4, 5, 6])
    tab("by enemies within 6", lambda s: min(s["n_near"], 4), [1, 2, 3, 4])
    tab("by result", lambda s: s["res"])
    tab("Prism by bag", lambda s: (("0-49" if s["bag"] < 50 else "50-199" if s["bag"] < 200 else "200+") if s["v"] == "Prism" else None), ["0-49", "50-199", "200+"], 10)
    tab("by round", lambda s: "r<=300" if s["r"] <= 300 else "r301-600" if s["r"] <= 600 else "r601+", ["r<=300", "r301-600", "r601+"])
