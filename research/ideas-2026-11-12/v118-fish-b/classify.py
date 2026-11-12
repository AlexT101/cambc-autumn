"""Assign every game a decisive mechanism from its replay timeline (feat.json), losses and wins by the same tests.

    py research/ideas-2026-11-12/v118-fish-b/classify.py [--list]      # -> replays/v118b/classes.json

The final wealth gap (tributed + carried, them - us) splits exactly into
    farm  = their capture gems - ours
    fight = 2 x (bags we lost to their champions - bags they lost to ours)      (a kill moves the bag: a double swing)
    camp  = bags we lost to camps - theirs
and the fight part into hoard (2 x our bags of 100+ gems lost to champions) and small (the rest, net of the bags we took);
the camp part likewise (our 100+ bags lost to camps, and the rest).
Tests, in order:
  FINISH-FAIL  one of our champions held the winning bag (our tributes + its bag >= 1000; winbag.py) and we lost: the
               carrier died with it (tag fin=died), or the game ended first (fin=time)
  RACE         we ended with at least their wealth, or with a winning total in tributes + bags: the gems were ours, unbanked
  otherwise the largest component names the game:
  HOARD-KILL   our 100+ bags killed (tag at_break: such a death within 15 rounds of the break round, the last round we were level)
  HOARD-CAMP   our 100+ bags lost to camps
  ATTRITION    small bags, net
  FARM-EARLY   farm, and behind by a tenth of the win (100 gems of wealth) at r300 already
  FARM-DEAD    farm, and our dead champion-rounds exceed theirs by a third of one champion's whole game
  FARM-LATE    farm otherwise
Wins get the same flags (whether the event happened)."""
import argparse, json, math
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BIG = 100


def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))


def flags(f):
    big_k = [d for d in f["deaths"] if d["us"] and not d["camp"] and d["bag"] >= BIG]
    big_c = [d for d in f["deaths"] if d["us"] and d["camp"] and d["bag"] >= BIG]
    hk = sum(d["bag"] for d in big_k); hc = sum(d["bag"] for d in big_c)
    cap300 = lambda side: sum(f[f"cap_{side}"][:2])  # r1-400 phases 0,1 ... refined below
    out = {"hk": hk, "hc": hc, "n_big_k": len(big_k), "n_big_c": len(big_c),
           "big_victims": [(d["v"], d["r"], d["bag"], d["by"] or "camp") for d in big_k + big_c],
           "race": f["end_wealth_us"] >= f["end_wealth_them"] or f["our_gems"] + f["end_carried_us"] >= 1000,
           "unbanked": f["end_carried_us"]}
    return out


def cap_to(f, side, r):
    # capture gems to round r from the wealth identity at the checkpoint: wealth = captures + taken - lost
    # (kills before r are few; use the earned-wealth curve directly as the standing measure)
    cps = f["cp_rounds"]; w = f[f"wealth_{side}"]
    i = max([j for j, x in enumerate(cps) if x <= r], default=None)
    return w[i] if i is not None else 0


def classify(f):
    fl = flags(f)
    g = f["gap"]
    hoard_k = 2 * fl["hk"]; small = f["gap_fight"] - hoard_k; hoard_c = fl["hc"]
    fl.update({"c_farm": f["gap_farm"], "c_hoard_k": hoard_k, "c_small": small, "c_hoard_c": hoard_c, "c_camp_other": f["gap_camp"] - hoard_c})
    fl["at_break"] = any(abs(r - f["break"]) <= 15 for _, r, _, _ in fl["big_victims"])
    lead300 = cap_to(f, "us", 300) - cap_to(f, "them", 300)
    fl["lead300"] = lead300; fl["dead_diff"] = (f["dead_share_us"] - f["dead_share_them"]) * f["npick"]
    wb = WINBAG.get(f["key"])
    fl["winbag_first"] = wb["first"] if wb else None
    if f["result"] == "win":
        return "WIN", fl
    if wb and wb["first"]:
        fl["fin"] = "died" if wb["died"] else "time"
        fl["fin_detail"] = {"who": wb["who"], "first": wb["first"], "bag": wb["bag0"], "held": wb["held"], "locks_after": wb["locks_after"], "died": wb["died"]}
        return "FINISH-FAIL", fl
    if fl["race"]:
        return "RACE", fl
    comp = max((("FARM", f["gap_farm"]), ("HOARD-KILL", hoard_k), ("ATTRITION", small), ("HOARD-CAMP", hoard_c)), key=lambda x: x[1])[0]
    if comp == "FARM":
        comp = "FARM-EARLY" if lead300 <= -100 else "FARM-DEAD" if fl["dead_diff"] >= 1 / 3 else "FARM-LATE"
    return comp, fl


WINBAG = {r["key"]: r for r in json.load(open(REPO / "replays/v118b/winbag.json"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    F = json.load(open(REPO / "replays/v118b/feat.json"))
    rows = []
    for f in F:
        c, fl = classify(f)
        rows.append({"key": f["key"], "map": f["map"], "side": f["side"], "npick": f["npick"], "result": f["result"], "end": f["end"],
                     "rounds": f["rounds"], "score": [f["our_gems"], f["opp_gems"]], "class": c, "gap": f["gap"], "farm": f["gap_farm"],
                     "fight": f["gap_fight"], "camp": f["gap_camp"], "break": f["break"], "has_prism": "Prism" in f["our_picks"], **fl})
    json.dump(rows, open(REPO / "replays/v118b/classes.json", "w"))
    L = [r for r in rows if r["result"] == "loss"]; W = [r for r in rows if r["result"] == "win"]
    print(f"{len(rows)} games: {len(W)} wins, {len(L)} losses")
    cnt = Counter(r["class"] for r in L)
    for c, n in cnt.most_common():
        S = [r for r in L if r["class"] == c]
        print(f"  {c:11} {n:3}  {100 * n / len(L):4.1f}% of losses   median gap {sorted(r['gap'] for r in S)[len(S) // 2]:5}  median break r{sorted(r['break'] for r in S)[len(S) // 2]}")
    print("flags in wins vs losses (the event happened at all):")
    for name, test in (("held the winning bag at some point", lambda r: r["winbag_first"] is not None), ("a 100+ bag lost to a champion", lambda r: r["n_big_k"] > 0), ("a 100+ bag lost to a camp", lambda r: r["n_big_c"] > 0),
                       ("ended holding 300+ unbanked gems", lambda r: r["unbanked"] >= 300)):
        kw, kl = sum(test(r) for r in W), sum(test(r) for r in L)
        n = kw + kl
        lo, hi = wilson(kw, n)
        print(f"  {name:34} wins {kw:3}/{len(W)}  losses {kl:3}/{len(L)}   win rate when it happens {100 * kw / max(1, n):.0f}% [{lo:.0f}-{hi:.0f}] of {n}; "
              f"otherwise {100 * (len(W) - kw) / max(1, len(rows) - n):.0f}% of {len(rows) - n}")
    if a.list:
        for r in sorted(L, key=lambda r: (r["class"], r["gap"])):
            print(f"{r['class']:11} {r['key']} {r['map'][:18]:18} {r['side']} n{r['npick']} r{r['rounds']:4} {r['score'][0]:4}-{r['score'][1]:4} gap {r['gap']:5} farm {r['farm']:5} fight {r['fight']:5} camp {r['camp']:4} break r{r['break']:4} unbanked {r['unbanked']:4} big {r['big_victims']}")


if __name__ == "__main__":
    main()
