"""How our bag carriers die: every death of ours to champions (replay only), with the fatal run of damage.

    py research/ideas-2026-11-12/v118-fish-b/deathctx.py     # -> replays/v118b/deathctx.json

Per death: the fatal run = champion damage to the victim with gaps of at most 2 rounds, ending at the death.
  hp0        health share when the run began;  ttk = death round - first hit round
  own_turns  the victim's own acting rounds strictly inside the run (0 = it never acted between first hit and death)
  dmg_by     damage by attacker type over the run;  burst = damage in the last 2 rounds / max health
  seen0      whether the victim saw its killer at the start of its last turn before the first hit, and the distance then
  last_act   what the victim did on that turn (attack/cast at a champion, at a camp, moved toward / away from the killer, channel)
  killer Str / max HP, allies and enemies within 8 of the victim when the run began."""
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
    dmg = {}
    for s, r, a, v, amt, ap, vp in g.champ_damage:
        dmg.setdefault(v, []).append((s, r, a, amt))
    acts = {}
    for e in g.events:
        if "a" in e and e["k"] in ("move", "attack", "cast", "tribute_start", "recall_start", "blocked"):
            acts.setdefault(e["a"], []).append(e)
    out = []
    for e in g.deaths:
        v = e["v"]
        if g.team_of[v] != us or "by" not in e or e.get("linked") is not None:
            continue
        hits = [h for h in dmg.get(v, []) if h[0] <= e["s"]]
        run = []
        for h in reversed(hits):
            if run and run[-1][1] - h[1] > 2:
                break
            if not run and e["r"] - h[1] > 2:
                break
            run.append(h)
        run.reverse()
        if not run:
            continue
        r0, s0 = run[0][1], run[0][0]
        a = ch[g.idx[v]]
        i0 = max(0, r0 - 2)
        mh = a["maxHp"][i0]; hp0 = a["hp"][i0] / mh if mh else 0
        own = sorted({x["r"] for x in acts.get(v, []) if s0 < x["s"] < e["s"]})
        stunned = sum(1 for r in range(r0, e["r"] + 1) if a["turn"][min(r, n) - 1] == 5)
        by = {}
        for s, r, at, amt in run:
            by[g.name_of[at]] = by.get(g.name_of[at], 0) + amt
        burst = sum(amt for s, r, at, amt in run if r >= e["r"] - 1) / mh
        k = e["by"]
        # the victim's last own action before the first hit
        prev = [x for x in acts.get(v, []) if x["s"] < s0]
        last = prev[-1] if prev else None
        last_r = last["r"] if last else None
        kpos0 = g.pos(k, i0); vpos0 = g.pos(v, i0)
        d0 = chebyshev(kpos0, vpos0) if kpos0 and vpos0 else None
        seen0 = k in a["sees"][min(r0, n) - 1] if r0 - 1 < n else None
        seen_prev = k in a["sees"][max(0, r0 - 2)]
        la = None
        if last and last_r is not None and last_r >= r0 - 2:
            if last["k"] in ("attack", "cast"):
                la = "hit_champ" if (last.get("tgt") is not None or any(x[0] in g.team_of for x in last.get("dmg", []))) else ("hit_camp" if (last.get("camp") is not None or last.get("cdmg")) else last["k"])
            elif last["k"] == "move" and kpos0:
                la = "toward" if chebyshev(last["to"], kpos0) < chebyshev(last["f"], kpos0) else ("away" if chebyshev(last["to"], kpos0) > chebyshev(last["f"], kpos0) else "sideways")
            else:
                la = last["k"]
        # rounds in the last 30 with the killer in the victim's sight
        seen_rounds = sum(1 for r in range(max(1, r0 - 30), r0) if k in a["sees"][r - 1])
        allies = sum(1 for c in g.team_ids[us] if c != v and g.pos(c, i0) and vpos0 and chebyshev(g.pos(c, i0), vpos0) <= 8)
        enem = sum(1 for c in g.team_ids[1 - us] if g.pos(c, i0) and vpos0 and chebyshev(g.pos(c, i0), vpos0) <= 8)
        kk = ch[g.idx[k]]
        own_half = g.map.half(g.map.own(us, tuple(e["at"])))
        out.append({"key": f["key"], "result": f["result"], "r": e["r"], "v": g.name_of[v], "bag": e["gems"], "by": g.name_of[k], "r0": r0,
                    "ttk": e["r"] - r0, "hp0": round(hp0, 2), "maxhp": round(mh), "own_turns": len(own), "stunned": stunned, "dmg_by": {t: round(x) for t, x in by.items()},
                    "burst": round(burst, 2), "d0": d0, "seen0": seen0, "seen_prev": seen_prev, "seen30": seen_rounds, "last_act": la, "allies8": allies,
                    "enemies8": enem, "by_str": round(kk["str"][i0]), "by_maxhp": round(kk["maxHp"][i0]), "half": {0: "own", 1: "enemy", -1: "mid"}[own_half],
                    "altar": g.map.altar_dist(tuple(e["at"])), "chan0": a["chan"][i0], "foc": round(a["foc"][i0]),
                    "our_trib": R["gems"][us][i0], "their_trib": R["gems"][1 - us][i0]})
    return out


if __name__ == "__main__":
    F = json.load(open(REPO / "replays/v118b/feat.json"))
    with ProcessPoolExecutor(24) as ex:
        rows = [d for ds in ex.map(one, F, chunksize=4) for d in ds]
    json.dump(rows, open(REPO / "replays/v118b/deathctx.json", "w"))
    print(len(rows), "deaths of ours to champions in", len(F), "games")
