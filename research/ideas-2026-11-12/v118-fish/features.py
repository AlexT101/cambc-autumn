"""Per-game and per-death tables for v118's Fish r8 games, from the harness's ladder extract.

    py research/ideas-2026-11-12/v118-fish/features.py [--threads 16]

Reads replays/v118/manifest.json and replays/v118/extract/ladder (extract.mjs tables, keys.json); writes
replays/v118/analysis/{games.jsonl, deaths.jsonl, captures.jsonl}. Everything is from the live replays; `us` is our
side of each game. Reuses tools/replay/analysis: macro.extract (break round, window cause, gem-margin components),
losses.extract (death episodes and their situation tags).

games.jsonl, one row a game:
  key, map, side, result, rounds, npicks, our_draft, opp_draft, set/part, end_reason, our/opp final gems
  cp: per checkpoint round (100..1000, and the end): for us and opp, lifetime gold, tributed, carried, capture gems and
      gold so far, kill gold so far, deaths, kills, bags lost to champions / camps, dead champion-rounds
  flow: whole-game gem flow per side (cap, taken, lostc, lostm, carried_end, tributed)
  macro: break round, window, cause and components (analysis/macro.py)
  champs: per champion of both sides: type, kills, deaths, earned gold, capture gems, gems lost, gems tributed,
      Strength / Focus / max HP at r300 / r600 / end, items at the end
  first tribute rounds, locks placed, tributes blocked, largest bag death, monolith captures
"""
import argparse, json, os, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
V = REPO / "replays/v118"
os.environ["CAMBC_ANALYSIS"] = str(V / "extract/ladder")
sys.path.insert(0, str(REPO / "tools/replay"))
from analysis import data as D  # noqa: E402
from analysis import macro as macro_mod, losses as losses_mod  # noqa: E402

CPS = [50, 100, 150, 200, 300, 400, 500, 600, 800, 1000]


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def one(arg):
    key, row, d = arg
    g = D.Game(d)
    us = 0 if row["our_side"] == "a" else 1
    op = 1 - us
    n, R, mp = g.n_rounds, g.rounds, g.map
    team_of, name_of = g.team_of, g.name_of
    assert (g.winner == us) == (row["result"] == "win"), key
    # cumulative per-round components per team
    comp = [defaultdict(lambda: [0.0] * (n + 2)) for _ in (0, 1)]
    caps, deaths = [], []
    first_trib = [None, None]
    trib_n = [0, 0]
    trib_gems = [[], []]
    locks = [0, 0]
    blocked = [0, 0]
    lock_hits = [0, 0]
    mono = [0, 0]
    gtypes = {grp["id"]: grp["types"] for grp in mp.groups}
    champ_cap = Counter()
    champ_lost = Counter()
    champ_trib = Counter()
    for e in g.events:
        k, r = e["k"], min(e["r"], n)
        if k == "capture":
            t = e["team"]
            gems = sum(s[1] for s in e["shares"])
            gold = sum(s[2] for s in e["shares"])
            comp[t]["cap"][r] += gems
            comp[t]["capgold"][r] += gold
            comp[t]["ncap"][r] += 1
            grp = mp.groups[e["g"]]
            side = grp["side"]
            # half in the capturing team's own frame: own / enemy / mid
            half = "mid" if side == -1 else ("own" if side == t else "enemy")
            comp[t]["cap_" + half][r] += gems
            if "Monolith" in grp["types"]:
                mono[t] += 1
                comp[t]["cap_mono"][r] += gems
            for cid, gm, _ in e["shares"]:
                champ_cap[cid] += gm
            caps.append({"key": key, "r": r, "us": t == us, "g": e["g"], "types": "".join(sorted(D.TYPE_ABBR[x] for x in grp["types"])),
                         "gems": gems, "gold": gold, "half": half, "holders": [name_of[s[0]] for s in e["shares"]]})
        elif k == "death":
            v = e["v"]
            t = team_of[v]
            bag = e.get("gems", 0)
            by = e.get("by")
            comp[t]["deaths"][r] += 0 if e.get("linked") is not None else 1
            if by is not None and by in team_of:
                comp[t]["lostc"][r] += bag
                comp[team_of[by]]["taken"][r] += bag
                comp[team_of[by]]["killgold"][r] += 0 if e.get("linked") is not None else e.get("gold", 0)
            else:
                comp[t]["lostm"][r] += bag
                comp[t]["campdeaths"][r] += 1
            champ_lost[v] += bag
        elif k == "tribute_end":
            t = team_of[e["a"]]
            if first_trib[t] is None:
                first_trib[t] = r
            trib_n[t] += 1
            trib_gems[t].append(e["gems"])
            champ_trib[e["a"]] += e["gems"]
        elif k == "lock_place":
            locks[e["team"]] += 1
        elif k == "tribute_blocked":
            blocked[team_of[e["a"]]] += 1
        elif k == "attack" and e.get("lock"):
            lock_hits[team_of[e["a"]]] += 1
    champs = R["champions"]
    nR = len(R["round"])

    def at(arr, r):
        i = min(r, nR) - 1
        return arr[i] if 0 <= i < len(arr) else None

    def cum(t, name, r):
        return sum(comp[t][name][: min(r, n) + 1])

    dead_rounds = [[0] * (n + 2) for _ in (0, 1)]
    for c in champs:
        for i in range(min(n, len(c["alive"]))):
            if not c["alive"][i]:
                dead_rounds[c["team"]][i + 1] += 1
    cp = {}
    for r in CPS + [n]:
        rr = min(r, n)
        ent = {}
        for t, lab in ((us, "us"), (op, "op")):
            ent[lab] = {
                "gold": sum((at(c["earned"], rr) or 0) for c in champs if c["team"] == t),
                "trib": at(R["gems"][t], rr),
                "carried": sum((at(c["gems"], rr) or 0) for c in champs if c["team"] == t),
                "cap": cum(t, "cap", rr), "capgold": cum(t, "capgold", rr), "ncap": cum(t, "ncap", rr),
                "cap_own": cum(t, "cap_own", rr), "cap_enemy": cum(t, "cap_enemy", rr), "cap_mid": cum(t, "cap_mid", rr),
                "cap_mono": cum(t, "cap_mono", rr),
                "killgold": cum(t, "killgold", rr), "deaths": cum(t, "deaths", rr), "campdeaths": cum(t, "campdeaths", rr),
                "lostc": cum(t, "lostc", rr), "lostm": cum(t, "lostm", rr), "taken": cum(t, "taken", rr),
                "dead_rounds": sum(dead_rounds[t][: rr + 1]),
                "alive": sum(1 for c in champs if c["team"] == t and at(c["alive"], rr)),
            }
        cp["end" if r == n and r not in CPS else str(r)] = ent
        if r == n:
            cp["end"] = ent
    M = macro_mod.extract(g)
    L = losses_mod.extract(g)
    G = M["game"]
    flow = {}
    for t, lab in ((us, "us"), (op, "op")):
        flow[lab] = {"cap": cum(t, "cap", n), "taken": cum(t, "taken", n), "lostc": cum(t, "lostc", n), "lostm": cum(t, "lostm", n),
                     "carried_end": sum((c["gems"][-1] or 0) for c in champs if c["team"] == t), "trib": g.final_gems[t]}
    ch_rows = []
    for c, m in zip(champs, g.champs):
        cid = c["id"]
        ch_rows.append({"id": cid, "us": c["team"] == us, "type": name_of[cid], "kills": m["kills"], "deaths": m["deaths"],
                        "earned": m["earnedGold"], "cap": champ_cap[cid], "lost": champ_lost[cid], "trib": champ_trib[cid],
                        "str": {str(r): at(c["str"], r) for r in (100, 300, 600)} | {"end": c["str"][-1]},
                        "foc": {str(r): at(c["foc"], r) for r in (100, 300, 600)} | {"end": c["foc"][-1]},
                        "maxhp": {str(r): at(c["maxHp"], r) for r in (100, 300, 600)} | {"end": c["maxHp"][-1]},
                        "gold": {str(r): at(c["earned"], r) for r in (100, 200, 300, 600)},
                        "items": c["items"][-1] if c.get("items") else None})
    # deaths with the losses.py situation tags
    for e in L["episodes"]:
        if e["kind"] not in ("death", "camp_death"):
            continue
        t = e["team"]
        tags = e.get("tags", {})
        killers = [name_of[x] for x in tags.get("killers", [])] if e["kind"] == "death" else []
        ev = next((x for x in g.deaths if x["v"] == e["cid"] and x["r"] == e["r"]), None)
        by = ev.get("by") if ev else None
        c = g.ch(e["cid"])
        i0 = max(0, e.get("r_hit", e["r"]) - 2)
        deaths.append({"key": key, "r": e["r"], "r_hit": e.get("r_hit"), "us": t == us, "kind": e["kind"], "victim": name_of[e["cid"]],
                       "vid": e["cid"], "by": name_of.get(by) if by is not None else None, "by_id": by, "bag": e["bag"], "cost": e["cost"],
                       "doing": tags.get("doing"), "num": tags.get("num"), "warn": tags.get("warn"), "wtag": tags.get("wtag"),
                       "approach": tags.get("approach"), "heading": tags.get("heading"), "half": tags.get("half"),
                       "allies8": tags.get("allies8"), "enemies8": tags.get("enemies8"), "allies16": tags.get("allies16"),
                       "killers": killers, "altar_d": tags.get("altar_d"), "prev": tags.get("prev"),
                       "cf_recall": bool(e.get("cf", {}).get("recall")), "cf_altar": e.get("cf", {}).get("altar"),
                       "hp_frac": (c["hp"][i0] / c["maxHp"][i0]) if c["maxHp"][i0] else None, "maxhp": c["maxHp"][i0],
                       "cause": ev.get("cause") if ev else None, "camp": tags.get("camp"), "at": ev.get("at") if ev else None,
                       "result": row["result"], "rounds": n})
    out = {
        "key": key, "dir": d, "map": row["map"], "side": row["our_side"], "result": row["result"], "rounds": n, "npicks": len(row["our_draft"]),
        "our_draft": row["our_draft"], "opp_draft": row["opp_draft"], "set": row.get("set"), "part": row.get("part"), "task": row.get("task"),
        "group": row["group_id"], "position": row["position"], "end_reason": row["end_reason"], "our_gems": g.final_gems[us], "opp_gems": g.final_gems[op],
        "W": mp.W, "H": mp.H, "altars": len(mp.altars), "ngroups": len(mp.groups), "cp": cp, "flow": flow,
        "macro": {"break": G["break"], "window": G["window"], "cause": G["cause"], "win_parts": G["win_parts"], "whole": G["whole"], "gap_after": G["gap_after"]},
        "champs": ch_rows, "first_trib": {"us": first_trib[us], "op": first_trib[op]}, "trib_n": {"us": trib_n[us], "op": trib_n[op]},
        "trib_gems": {"us": trib_gems[us], "op": trib_gems[op]},
        "locks": {"us": locks[us], "op": locks[op]}, "blocked": {"us": blocked[us], "op": blocked[op]}, "lock_hits": {"us": lock_hits[us], "op": lock_hits[op]},
        "mono": {"us": mono[us], "op": mono[op]},
        "loss_sides": {"us": L["sides"][us], "op": L["sides"][op]},
        "stalls": {"us": sum(e["cost"] for e in L["episodes"] if e["kind"] == "stall" and e["team"] == us),
                   "op": sum(e["cost"] for e in L["episodes"] if e["kind"] == "stall" and e["team"] == op)},
        "camp_lost": {"us": [(e["r"], e["cost"], e["key"][1] if len(e["key"]) > 1 else None) for e in L["episodes"] if e["kind"] == "camp_lost" and e["team"] == us],
                      "op": [(e["r"], e["cost"], e["key"][1] if len(e["key"]) > 1 else None) for e in L["episodes"] if e["kind"] == "camp_lost" and e["team"] == op]},
        "turns": {lab: {ph: dict(M["sides"][t].get("turns_" + ph, {})) for ph in ()} for t, lab in ((us, "us"), (op, "op"))},
        "msides": {"us": {k: v for k, v in M["sides"][us].items() if isinstance(v, (int, float))},
                   "op": {k: v for k, v in M["sides"][op].items() if isinstance(v, (int, float))}},
    }
    return out, deaths, caps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=16)
    a = ap.parse_args()
    man = {f"{g['group'][:8]}-{g['position']}": g for g in json.loads((V / "manifest.json").read_text())["games"]}
    keys = json.loads((V / "extract/ladder/keys.json").read_text())
    jobs = [(k, man[k], keys[k]["dir"]) for k in man if k in keys and keys[k]["ok"]]
    print(f"{len(jobs)} of {len(man)} manifest games extracted", flush=True)
    out = V / "analysis"
    out.mkdir(exist_ok=True)
    with ProcessPoolExecutor(a.threads) as ex, open(out / "games.jsonl", "w") as fg, open(out / "deaths.jsonl", "w") as fd, open(out / "captures.jsonl", "w") as fc:
        for row, deaths, caps in ex.map(one, jobs, chunksize=2):
            fg.write(json.dumps(row) + "\n")
            for x in deaths:
                fd.write(json.dumps(x) + "\n")
            for x in caps:
                fc.write(json.dumps(x) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
