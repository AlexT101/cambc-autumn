"""Combat regret of ocean's choices at fork points, net of noise (research/combat-lab/analyst-findings.md).

    py tools/combatlab/fork_regret.py DIR [DIR...] [--mark 30] [--out rows.jsonl] [--report]

Reads fork_sweep / forkgame output (DIR/forks.jsonl, DIR/games.jsonl), with noise replicates if the run had them
(forkgame --jitter / --skip-reps: rep 0 is the real continuation). Writes one row per fork: situation tags, ocean's
action and its class, and per arm (the `none` arm and each forced one) its class and per-rep combat and economy
scores at each mark. --report prints the noise floor and the per-class gains.

Combat score of the decider's team at a mark, as changes since the fork (own minus enemy):
    C = kills - deaths  (bodies; Cassi and Issac 0.5 each, they die together)
        + 0.5 * hp      (sum over champions alive throughout of the change in health / max health)
        + bags          (per champion who died in the window, min(gems carried at the fork, 80) / 80: theirs +,
                         ours -; capped because bags of hundreds of gems would make the score all bag)
    So a death is 1 to 2 (with a bag of 80+), a full health bar 0.5. bags_raw keeps the uncapped gems.
KD is CL without the health term (bodies and bags only: sparse, but free of heal-at-home credit).
CL is C over the champions alive within 12 of the decider at the fork only (less noise from fights elsewhere).
Economy score, kept apart: E = trib + gems carried (both gem units; own minus enemy) and W = wealth (gold + items).
"""
import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TYPES = ["ryth", "vesper", "vendetta", "cassi", "issac", "stellar", "prism", "marcella", "willow", "ren", "varg", "tavi", "hor"]
RANGED = {"vesper", "cassi", "stellar", "prism", "willow", "tavi"}
W_HP, BAG_CAP = 0.5, 80
LOCAL = 12  # CL: the champions alive within this of the decider at the fork


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def rect_dist(p, s):
    dx = max(s["minX"] - p[0], 0, p[0] - s["maxX"])
    dy = max(s["minY"] - p[1], 0, p[1] - s["maxY"])
    return max(dx, dy)


def load_maps(paths, cache):
    cache = Path(cache)
    have = {}
    if cache.exists():
        for l in open(cache):
            d = json.loads(l)
            have[d["file"]] = d
    need = sorted({p for p in paths if Path(p).stem not in have})
    if need:
        tmp = cache.with_suffix(".new")
        for i in range(0, len(need), 200):
            subprocess.run(["node", str(ROOT / "tools/combatlab/mapjson.mjs"), str(tmp)] + need[i:i + 200], check=True)
            with open(cache, "a") as f:
                for l in open(tmp):
                    f.write(l)
                    d = json.loads(l)
                    have[d["file"]] = d
        tmp.unlink()
    for d in have.values():
        if "_sets" not in d:
            d["_bush"] = {tuple(t) for t in d["bushes"]}
            d["_wall"] = {tuple(t) for t in d["walls"]}
            d["_sets"] = True
    return have


def body_w(t):
    return 0.5 if TYPES[t] in ("cassi", "issac") else 1.0


def scores(arm, fk, mark):
    at = arm["at"].get(str(mark))
    if at is None:
        return None
    t = fk["team"]
    dec = next(ch for ch in fk["champions"] if ch["id"] == fk["decider"])
    out = {}
    for scope in ("all", "local"):
        c = {"kills": 0.0, "deaths": 0.0, "hp": 0.0, "bags": 0.0, "bags_raw": 0.0}
        for ch in fk["champions"]:
            if scope == "local" and not (ch["alive"] and ch["x"] is not None and cheb((ch["x"], ch["y"]), (dec["x"], dec["y"])) <= LOCAL):
                continue
            m = at["champions"][str(ch["id"])]
            own = ch["team"] == t
            sgn = 1 if own else -1
            bw = body_w(ch["type"])
            if m["deaths"] > 0:
                if own:
                    c["deaths"] += bw * m["deaths"]
                else:
                    c["kills"] += bw * m["deaths"]
                if ch["alive"]:
                    c["bags"] -= sgn * min(ch["gems"], BAG_CAP) / BAG_CAP
                    c["bags_raw"] -= sgn * ch["gems"]
            elif ch["alive"] and m["alive"] and ch["max_hp"] and m["max_hp"]:
                c["hp"] += sgn * (m["hp"] / m["max_hp"] - ch["hp"] / ch["max_hp"])
        out[scope] = c
    c = out["all"]
    C = c["kills"] - c["deaths"] + W_HP * c["hp"] + c["bags"]
    cl = out["local"]
    CL = cl["kills"] - cl["deaths"] + W_HP * cl["hp"] + cl["bags"]
    own, opp = at["teams"][t], at["teams"][1 - t]
    base = [{"gems": 0, "wealth": 0} for _ in range(2)]
    for ch in fk["champions"]:
        base[ch["team"]]["gems"] += ch["gems"] if ch["alive"] else 0
        base[ch["team"]]["wealth"] += ch["gold"] + ch["items"]
    tr = fk["trib"]
    E = (own["trib"] - tr[t]) - (opp["trib"] - tr[1 - t]) + (own["gems"] - base[t]["gems"]) - (opp["gems"] - base[1 - t]["gems"])
    Wl = (own["gold"] + own["items"] - base[t]["wealth"]) - (opp["gold"] + opp["items"] - base[1 - t]["wealth"])
    me = at["champions"][str(fk["decider"])]
    KD = cl["kills"] - cl["deaths"] + cl["bags"]
    return {"C": round(C, 4), "CL": round(CL, 4), "KD": round(KD, 4), "E": E, "W": Wl, "self_dead": int(me["deaths"] > 0), **{k: round(v, 3) for k, v in c.items()}}


def situation(fk, mp, none_first):
    t, dec = fk["team"], fk["decider"]
    ch = {c["id"]: c for c in fk["champions"]}
    me = ch[dec]
    p = (me["x"], me["y"])
    enemies = [c for c in fk["champions"] if c["team"] != t and c["alive"] and c["x"] is not None]
    allies = [c for c in fk["champions"] if c["team"] == t and c["alive"] and c["x"] is not None and c["id"] != dec]
    side = t if not fk.get("swap") else t  # spawn index = team (team 0 is A)
    own_sp, en_sp = mp["spawn"][t], mp["spawn"][1 - t]
    de = sorted((cheb(p, (e["x"], e["y"])), e["id"]) for e in enemies)
    near = ch[de[0][1]] if de else None
    hpf = lambda c: c["hp"] / c["max_hp"] if c["max_hp"] else 0
    w8 = lambda xs, r: [c for c in xs if cheb(p, (c["x"], c["y"])) <= r]
    e8, a8 = w8(enemies, 8), w8(allies, 8)
    e4, a4 = w8(enemies, 4), w8(allies, 4)
    hp_own = me["hp"] + sum(c["hp"] for c in a8)
    hp_en = sum(c["hp"] for c in e8)
    s = {
        "dtype": TYPES[me["type"]], "ranged": TYPES[me["type"]] in RANGED, "hp": round(hpf(me), 3), "gems": me["gems"],
        "round": fk["round"], "branch": (none_first or {}).get("branch", ""),
        "d_enemy": de[0][0] if de else 99, "near_type": TYPES[near["type"]] if near else "", "near_hp": round(hpf(near), 3) if near else None,
        "near_id": near["id"] if near else None, "near_gems": near["gems"] if near else 0,
        "e4": len(e4), "e8": len(e8), "a4": len(a4), "a8": len(a8),
        "hp_ratio": round(hp_own / hp_en, 3) if hp_en else 9.0,
        "home": rect_dist(p, own_sp), "enemy_home": rect_dist(p, en_sp),
        "near_home": rect_dist((near["x"], near["y"]), mp["spawn"][1 - t]) if near else 99,
        "near_our_home": rect_dist((near["x"], near["y"]), own_sp) if near else 99,
        "cd": me["cd"], "near_cd": near["cd"] if near else None,
        "bush": p in mp["_bush"], "bush2": sum(1 for x in range(p[0] - 2, p[0] + 3) for y in range(p[1] - 2, p[1] + 3) if (x, y) in mp["_bush"]),
        "camps5": sum(1 for c in mp["camps"] if cheb(p, (c["x"], c["y"])) <= 5),
        "trigger": [x.split(":")[0] for x in fk["trigger"]],
        "enemy_low": min((hpf(c) for c in e8), default=None),
    }
    return s


def classify(lab, first, fk, s, mp):
    """An action class from geometry only (no outcome): kind + direction relative to the nearest enemy and home."""
    k = lab["kind"]
    ch = {c["id"]: c for c in fk["champions"]}
    me = ch[fk["decider"]]
    p = (me["x"], me["y"])
    near = ch.get(s["near_id"]) if s["near_id"] is not None else None
    own_sp = mp["spawn"][fk["team"]]
    span = lab.get("span", 1)
    sp = f"x{span}" if span != 1 else ""
    if k in ("walk", "dash"):
        q = (lab["x"], lab["y"])
        de = cheb(q, (near["x"], near["y"])) - cheb(p, (near["x"], near["y"])) if near else 0
        dh = rect_dist(q, own_sp) - rect_dist(p, own_sp)
        d = "away" if de > 0 else "toward" if de < 0 else "side"
        h = "home" if dh < 0 else "out" if dh > 0 else "level"
        return f"{k}:{d}:{h}{sp}", {"de": de, "dh": dh}
    if k == "attack":
        tgt = ch[lab["target"]]
        low = s["enemy_low"] is not None and abs(tgt["hp"] / tgt["max_hp"] - s["enemy_low"]) < 1e-6
        return f"attack:{'near' if lab['target'] == s['near_id'] else 'other'}{':low' if low else ''}{sp}", {}
    if k == "cast_enemy":
        return f"cast_enemy/s{lab.get('slot')}:{'near' if lab['target'] == s['near_id'] else 'other'}{sp}", {}
    if k in ("ground", "cast_self", "cast_ally"):
        return f"{k}/s{lab.get('slot')}{sp}", {}
    if k in ("home", "chase"):
        return f"{k}={lab.get('verdict')}x{span}", {}
    return k + sp, {}


def ocean_class(first, fk, s, mp):
    """Ocean's own action, from its first turn's outcome: where it went and what it hit."""
    if not first:
        return "dead"
    ch = {c["id"]: c for c in fk["champions"]}
    me = ch[fk["decider"]]
    p = (me["x"], me["y"])
    to = tuple(first.get("to") or p)
    hit_enemy = any(h[0] in ch and ch[h[0]]["team"] != fk["team"] for h in first.get("hits", []))
    near = ch.get(s["near_id"]) if s["near_id"] is not None else None
    if to == p:
        mv = "stay"
    else:
        de = cheb(to, (near["x"], near["y"])) - cheb(p, (near["x"], near["y"])) if near else 0
        dh = rect_dist(to, mp["spawn"][fk["team"]]) - rect_dist(p, mp["spawn"][fk["team"]])
        mv = ("dash" if cheb(to, p) > 1 else "walk") + ":" + ("away" if de > 0 else "toward" if de < 0 else "side") + ":" + (
            "home" if dh < 0 else "out" if dh > 0 else "level")
    return mv + ("+hit" if hit_enemy else "")


def half_of(game):
    m = game.split("#")[0]
    return int(hashlib.md5(m.encode()).hexdigest(), 16) % 2


def build(dirs, marks):
    rows = []
    for d in dirs:
        d = Path(d)
        games = {json.loads(l)["id"]: json.loads(l) for l in open(d / "games.jsonl")}
        mps = load_maps([g["map"] for g in games.values()], ROOT / "tools/combatlab/.mapcache.jsonl")
        forks, arms = {}, defaultdict(lambda: defaultdict(dict))
        for l in open(d / "forks.jsonl"):
            try:
                x = json.loads(l)
            except json.JSONDecodeError:  # a run still writing
                continue
            if x.get("type") == "fork":
                forks[(x["game"], x["fork"])] = x
            elif x.get("type") == "arm":
                arms[(x["game"], x["fork"])][x["arm"]][x.get("rep", 0)] = x
        for key, fk in forks.items():
            al = arms.get(key)
            if not al:
                continue
            mp = mps[Path(games[key[0]]["map"]).stem]
            none = [a for a in al.values() if 0 in a and a[0]["label"]["kind"] == "none"]
            if not none:
                continue
            nf = none[0][0].get("first")
            if next(c for c in fk["champions"] if c["id"] == fk["decider"])["x"] is None:
                continue
            s = situation(fk, mp, nf)
            out = []
            for j, reps in sorted(al.items()):
                a0 = reps.get(0)
                if a0 is None:
                    continue
                lab = a0["label"]
                if lab["kind"] == "none":
                    cls, geo = "none", {}
                else:
                    cls, geo = classify(lab, a0.get("first"), fk, s, mp)
                sc = {str(mk): [scores(reps[r], fk, mk) for r in sorted(reps)] for mk in marks}
                same = a0.get("first") is not None and nf is not None and lab["kind"] != "none" and lab.get("span", 1) == 1 and (
                    a0["first"].get("to") == nf.get("to") and sorted(map(tuple, a0["first"].get("hits", []))) == sorted(map(tuple, nf.get("hits", [])))
                    and a0["first"].get("cd") == nf.get("cd"))
                if lab["kind"] in ("home", "chase"):
                    # A forced verdict that ocean would have reached anyway changes nothing.
                    same = a0.get("branches") == none[0][0].get("branches") and sc == {
                        str(mk): [scores(none[0][r], fk, mk) for r in sorted(none[0])] for mk in marks}
                out.append({"arm": j, "label": lab, "cls": cls, "geo": geo, "same_as_ocean": same, "res": (a0.get("first") or {}).get("res"),
                            "reps": [reps[r].get("skip", reps[r].get("jitter", 0)) if r else 0 for r in sorted(reps)], "sc": sc,
                            "branches": a0.get("branches", "")})
            rows.append({"src": str(d), "game": key[0], "fork": key[1], "half": half_of(key[0]), "round": fk["round"], "decider": fk["decider"],
                         "team": fk["team"], "sit": s, "ocean": ocean_class(nf, fk, s, mp), "ocean_first": nf, "arms": out,
                         "pos": {c["id"]: [c["x"], c["y"], c["hp"], c["max_hp"], TYPES[c["type"]], c["team"], c["cd"], c["gems"]] for c in fk["champions"] if c["alive"] and c["x"] is not None}})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--marks", default="10,30,60")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    marks = [int(x) for x in a.marks.split(",")]
    rows = build(a.dirs, marks)
    with open(a.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{len(rows)} forks -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
