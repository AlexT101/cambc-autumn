"""Per-game timeline features of v118's games against Fish r8, from the extract (replays/v118b/analysis).

    py research/ideas-2026-11-12/v118-fish-b/feat.py [--jobs 24]      # -> replays/v118b/feat.json

One row per game on disk (key = group[-8:]-position), everything in our frame ("us"/"them"):
  curves   wealth (tributed + carried gems), tributed, earned gold, alive champion-rounds, every 50 rounds
  flow     capture gems, bags lost to champions / camps, kill gems taken, by phase
  deaths   every death: round, victim type, team, bag, killer type (or camp), half in the victim's frame, numbers within 8
  break    the last round the loser's wealth was at least the winner's
  decomp   final wealth gap = farm (capture gems) + fight (2 x net bags lost to champions) + camp (bags lost to camps)
  captures by half, monoliths; tributes (first, count, sizes, cancels); locks; Fish Vesper's and our carry's stats.
"""
import argparse, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "replays/v118b"
import os
os.environ["CAMBC_ANALYSIS"] = str(OUT / "analysis")
sys.path.insert(0, str(REPO / "tools/replay"))
from analysis.data import Game, load_index, chebyshev  # noqa: E402

STEP = 50
PHASES = [(1, 150), (151, 400), (401, 800), (801, 2000)]


def phase(r):
    for i, (a, b) in enumerate(PHASES):
        if a <= r <= b:
            return i
    return 3


def one(args):
    d, key, row = args
    g = Game(d)
    us = 0 if row["side"] == "a" else 1
    them = 1 - us
    R = g.rounds
    n = len(R["round"])
    ch = R["champions"]
    ids = {t: [c["id"] for c in g.champs if c["team"] == t] for t in (0, 1)}
    typ = g.name_of
    f = {"key": key, "dir": d, "map": row["map"], "side": row["side"], "result": row["result"], "rounds": row["rounds"],
         "end": row["end_reason"], "our_gems": row["our_gems"], "opp_gems": row["opp_gems"], "our_picks": row["our_picks"],
         "opp_picks": row["opp_picks"], "set": row["set"], "part": row["part"], "group": row["group"], "position": row["position"],
         "W": g.map.W, "H": g.map.H, "n_altars": len(g.map.altars), "npick": len(row["our_picks"])}
    assert g.final_gems[us] == row["our_gems"] and g.final_gems[them] == row["opp_gems"], (key, g.final_gems, row["our_gems"], row["opp_gems"])

    def carried(t, i):
        return sum(ch[g.idx[c]]["gems"][i] for c in ids[t])

    def earned(t, i):
        return sum(ch[g.idx[c]]["earned"][i] for c in ids[t])

    wealth = {t: [R["gems"][t][i] + carried(t, i) for i in range(n)] for t in (0, 1)}
    idxs = list(range(STEP - 1, n, STEP)) + ([n - 1] if (n % STEP) else [])
    f["cp_rounds"] = [i + 1 for i in idxs]
    for name, t in (("us", us), ("them", them)):
        f[f"wealth_{name}"] = [wealth[t][i] for i in idxs]
        f[f"trib_{name}"] = [R["gems"][t][i] for i in idxs]
        f[f"gold_{name}"] = [earned(t, i) for i in idxs]
        alive = [sum(ch[g.idx[c]]["alive"][i] for c in ids[t]) for i in range(n)]
        dead_cum, s = [], 0
        for i in range(n):
            s += len(ids[t]) - alive[i]
            dead_cum.append(s)
        f[f"deadrounds_{name}"] = [dead_cum[i] for i in idxs]
        f[f"dead_share_{name}"] = dead_cum[-1] / (n * len(ids[t]))
        f[f"end_carried_{name}"] = carried(t, n - 1)
        f[f"end_wealth_{name}"] = wealth[t][n - 1]
    win_t = us if row["result"] == "win" else them
    lose_t = 1 - win_t
    br = 0
    for i in range(n):
        if wealth[lose_t][i] >= wealth[win_t][i]:
            br = i + 1
    f["break"] = br
    # the largest lead we ever held, and when
    lead = [wealth[us][i] - wealth[them][i] for i in range(n)]
    f["max_lead"] = max(lead); f["max_lead_r"] = lead.index(max(lead)) + 1
    f["min_lead"] = min(lead); f["min_lead_r"] = lead.index(min(lead)) + 1
    f["lead_cp"] = [lead[i] for i in idxs]

    cap = {us: [0] * 4, them: [0] * 4}; capgold = {us: [0] * 4, them: [0] * 4}
    cap_half = {us: defaultdict(int), them: defaultdict(int)}; cap_n = {us: defaultdict(int), them: defaultdict(int)}
    cap_type = {us: defaultdict(int), them: defaultdict(int)}
    lostc = {us: [0] * 4, them: [0] * 4}; lostcamp = {us: [0] * 4, them: [0] * 4}
    deaths = []; tributes = {us: [], them: []}; tcancel = {us: defaultdict(int), them: defaultdict(int)}
    locks = {us: [], them: []}; tblocked = {us: 0, them: 0}; lock_destroyed = {us: 0, them: 0}
    cap_by_champ = defaultdict(lambda: [0, 0]); kills_by = defaultdict(int)
    shops = defaultdict(list)
    for e in g.events:
        k, r = e["k"], e["r"]
        if k == "capture":
            t = e["team"]; grp = g.map.groups[e["g"]]
            gems = sum(s[1] for s in e["shares"]); gold = sum(s[2] for s in e["shares"])
            cap[t][phase(r)] += gems; capgold[t][phase(r)] += gold
            side = grp["side"]
            half = "mid" if side == -1 else ("own" if side == t else "enemy")
            cap_half[t][half] += gems; cap_n[t][half] += 1
            if "Monolith" in grp["types"]:
                cap_type[t]["monolith"] += 1; cap_type[t]["monolith_gems"] += gems
            if "Golem" in grp["types"]:
                cap_type[t]["golem"] += 1
            for cid, gm, gd in e["shares"]:
                cap_by_champ[cid][0] += gm; cap_by_champ[cid][1] += gd
        elif k == "death":
            v = e["v"]; t = g.team_of[v]
            if e.get("linked") is not None:
                # the partner body's bag counts, the death itself once
                if "by" in e: lostc[t][phase(r)] += e["gems"]
                else: lostcamp[t][phase(r)] += e["gems"]
                deaths.append({"r": r, "v": typ[v], "vid": v, "us": t == us, "bag": e["gems"], "linked": True,
                               "by": typ.get(e.get("by")), "camp": "camp" in e})
                continue
            at = tuple(e["at"]); i0 = max(0, r - 2)
            allies = sum(1 for c in ids[t] if c != v and g.pos(c, i0) and chebyshev(g.pos(c, i0), at) <= 8)
            enem = sum(1 for c in ids[1 - t] if g.pos(c, i0) and chebyshev(g.pos(c, i0), at) <= 8)
            own = g.map.own(t, at); h = g.map.half(own)
            dd = {"r": r, "v": typ[v], "vid": v, "us": t == us, "bag": e["gems"], "by": typ.get(e.get("by")), "byid": e.get("by"),
                  "camp": "camp" in e, "half": {0: "own", 1: "enemy", -1: "mid"}[h], "allies8": allies, "enemies8": enem,
                  "altar": g.map.altar_dist(at), "maxhp": ch[g.idx[v]]["maxHp"][i0], "cause": e.get("cause")}
            if "by" in e:
                lostc[t][phase(r)] += e["gems"]; kills_by[e["by"]] += 1
                b = e["by"]; dd["by_str"] = ch[g.idx[b]]["str"][i0]; dd["by_maxhp"] = ch[g.idx[b]]["maxHp"][i0]
            else:
                lostcamp[t][phase(r)] += e["gems"]
            deaths.append(dd)
        elif k == "tribute_end":
            tributes[g.team_of[e["a"]]].append((r, e["gems"], typ[e["a"]]))
        elif k == "tribute_cancel":
            tcancel[g.team_of[e["a"]]][e.get("cause", "?")] += 1
        elif k == "tribute_blocked":
            tblocked[g.team_of[e["a"]]] += 1
        elif k == "lock_place":
            locks[e["team"]].append(r)
        elif k == "lock_destroyed":
            lock_destroyed[e["team"]] += 1
        elif k == "shop" and e.get("items"):
            for it, dn in e["items"].items():
                if dn > 0 and "Emblem" in it:
                    shops[e["a"]].append((r, it))
    for name, t in (("us", us), ("them", them)):
        f[f"cap_{name}"] = cap[t]; f[f"capgold_{name}"] = capgold[t]
        f[f"cap_half_{name}"] = dict(cap_half[t]); f[f"capn_half_{name}"] = dict(cap_n[t]); f[f"cap_type_{name}"] = dict(cap_type[t])
        f[f"lostc_{name}"] = lostc[t]; f[f"lostcamp_{name}"] = lostcamp[t]
        f[f"tributes_{name}"] = tributes[t]; f[f"tcancel_{name}"] = dict(tcancel[t]); f[f"tblocked_{name}"] = tblocked[t]
        f[f"locks_{name}"] = locks[t]; f[f"lock_destroyed_{name}"] = lock_destroyed[t]
    f["deaths"] = deaths
    # exact decomposition of the final wealth gap (them - us)
    C = {t: sum(cap[t]) for t in (us, them)}; L = {t: sum(lostc[t]) for t in (us, them)}; K = {t: sum(lostcamp[t]) for t in (us, them)}
    f["gap"] = wealth[them][n - 1] - wealth[us][n - 1]
    f["gap_farm"] = C[them] - C[us]; f["gap_fight"] = 2 * (L[us] - L[them]); f["gap_camp"] = K[us] - K[them]
    f["gap_check"] = f["gap_farm"] + f["gap_fight"] + f["gap_camp"] - f["gap"]

    # champions: both teams, stats at r100/300/600 and at the end
    champs = []
    for c in g.champs:
        a = ch[g.idx[c["id"]]]
        def at(r, k):
            return a[k][min(r, n) - 1]
        champs.append({"id": c["id"], "type": c["name"], "us": c["team"] == us, "kills": c["kills"], "deaths": c["deaths"],
                       "earned": c["earnedGold"], "earned_cp": [at(r, "earned") for r in (100, 200, 300, 600)],
                       "str_cp": [round(at(r, "str")) for r in (100, 300, 600)], "maxhp_cp": [round(at(r, "maxHp")) for r in (100, 300, 600)],
                       "foc_cp": [round(at(r, "foc")) for r in (100, 300, 600)],
                       "cap_gems": cap_by_champ[c["id"]][0], "cap_gold": cap_by_champ[c["id"]][1], "maxbag": max(a["gems"]),
                       "maxbag_r": a["gems"].index(max(a["gems"])) + 1, "emblems": shops.get(c["id"], []),
                       "submitted": c["stats"]["submittedGems"], "champ_dmg": round(c["stats"]["championDamageDone"]),
                       "champ_taken": round(c["stats"]["championDamageTaken"]), "monster_dmg": round(c["stats"]["monsterDamageDone"]),
                       "dead_rounds": sum(1 for x in a["alive"] if not x), "prio_sample": [a["prio"][i] for i in (0, min(n - 1, 99), min(n - 1, 299))]})
    f["champs"] = champs
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=24)
    a = ap.parse_args()
    rows = {f"{g['group'][-8:]}-{g['position']}": g for g in json.load((REPO / "replays/pulls/v118-fish-2026-11-12.json").open())}
    jobs = []
    for r in load_index():
        p = Path(r["source"])
        if p.parts[:3] != ("replays", "v118b", "groups"):
            continue
        key = f"{p.parts[3]}-{p.name.split('-')[0]}"
        jobs.append((r["dir"], key, rows[key]))
    with ProcessPoolExecutor(a.jobs) as ex:
        out = list(ex.map(one, jobs, chunksize=4))
    out.sort(key=lambda f: f["key"])
    (OUT / "feat.json").write_text(json.dumps(out))
    print(f"{len(out)} games of {len(rows)} -> {OUT / 'feat.json'}; decomposition residual max {max(abs(f['gap_check']) for f in out)}")


if __name__ == "__main__":
    main()
