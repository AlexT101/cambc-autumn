"""Fish's Vesper against our Prism, wins and losses alike (replay only).

    py research/ideas-2026-11-12/v118-fish-b/hunts.py     # -> replays/v118b/hunts.json

An episode is a run of Fish-Vesper damage to our Prism with gaps of at most 2 rounds. Per episode: rounds, the Prism's bag,
health share and max health at the start, Vesper's Strength and max health, whether the Prism died in it (to anyone),
allies / enemies within 8 at the start, damage the Prism and our team dealt to Vesper during it, and the Prism's net walk
relative to Vesper (first and last distance). Also per game: both carries' stats every 100 rounds."""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
os.environ["CAMBC_ANALYSIS"] = str(REPO / "replays/v118b/analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
from analysis.data import Game, chebyshev  # noqa: E402


def one(f):
    g = Game(f["dir"]); us = 0 if f["side"] == "a" else 1
    R = g.rounds; ch = R["champions"]; n = len(R["round"])
    P = [c["id"] for c in g.champs if c["team"] == us and c["name"] == "Prism"]
    V = [c["id"] for c in g.champs if c["team"] != us and c["name"] == "Vesper Vale"]
    curves = {}
    for name, ids in (("prism", P), ("fvesper", V)):
        if ids:
            a = ch[g.idx[ids[0]]]
            curves[name] = {k: [round(a[k][min(r, n) - 1]) for r in range(100, 1001, 100)] for k in ("str", "maxHp", "foc", "gems", "earned")}
    out = {"key": f["key"], "result": f["result"], "curves": curves, "eps": [], "rounds": n}
    if not P or not V:
        return out
    p, v = P[0], V[0]
    hits = [(s, r, amt) for s, r, a, vic, amt, *_ in g.champ_damage if a == v and vic == p]
    back = [(s, r, a, amt) for s, r, a, vic, amt, *_ in g.champ_damage if vic == v and g.team_of[a] == us]
    deaths = {e["r"]: e for e in g.deaths if e["v"] == p}
    eps = []
    for s, r, amt in hits:
        if eps and r - eps[-1]["r1"] <= 2:
            eps[-1]["r1"] = r; eps[-1]["dmg"] += amt; eps[-1]["s1"] = s
        else:
            eps.append({"r0": r, "r1": r, "dmg": amt, "s0": s, "s1": s})
    a, b = ch[g.idx[p]], ch[g.idx[v]]
    for e in eps:
        i0 = max(0, e["r0"] - 2)
        died = next((d for r, d in deaths.items() if e["r0"] <= r <= e["r1"] + 2), None)
        pp, vp = g.pos(p, i0), g.pos(v, i0)
        i1 = min(n - 1, e["r1"] - 1)
        pp1, vp1 = g.pos(p, i1), g.pos(v, i1)
        e.update({"bag": a["gems"][i0], "hp0": round(a["hp"][i0] / a["maxHp"][i0], 2), "pmax": round(a["maxHp"][i0]), "pfoc": round(a["foc"][i0]),
                  "vstr": round(b["str"][i0]), "vmax": round(b["maxHp"][i0]), "vhp0": round(b["hp"][i0] / b["maxHp"][i0], 2),
                  "died": died is not None, "killer": g.name_of.get(died.get("by")) if died else None, "lost": died["gems"] if died else 0,
                  "d0": chebyshev(pp, vp) if pp and vp else None, "d1": chebyshev(pp1, vp1) if pp1 and vp1 else None,
                  "allies8": sum(1 for c in g.team_ids[us] if c != p and g.pos(c, i0) and pp and chebyshev(g.pos(c, i0), pp) <= 8),
                  "enemies8": sum(1 for c in g.team_ids[1 - us] if g.pos(c, i0) and pp and chebyshev(g.pos(c, i0), pp) <= 8),
                  "prism_dmg_to_v": round(sum(x[3] for x in back if x[2] == p and e["r0"] - 1 <= x[1] <= e["r1"] + 1)),
                  "team_dmg_to_v": round(sum(x[3] for x in back if e["r0"] - 1 <= x[1] <= e["r1"] + 1)),
                  "v_died": any(d["v"] == v and e["r0"] <= d["r"] <= e["r1"] + 3 for d in g.deaths),
                  "half": {0: "own", 1: "enemy", -1: "mid"}[g.map.half(g.map.own(us, pp))] if pp else None})
        del e["s0"], e["s1"]
    out["eps"] = eps
    return out


if __name__ == "__main__":
    F = json.load(open(REPO / "replays/v118b/feat.json"))
    with ProcessPoolExecutor(20) as ex:
        rows = list(ex.map(one, F, chunksize=4))
    json.dump(rows, open(REPO / "replays/v118b/hunts.json", "w"))
    print(len(rows), "games,", sum(len(r["eps"]) for r in rows), "Vesper-on-Prism episodes")
