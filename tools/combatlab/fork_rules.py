"""Concrete one-arm rules (no outcome selection): per fork the rule picks at most one arm from geometry; its gain
over ocean's own action, mean over reps, with a bootstrap CI over games, per half and per rows file.

    py tools/combatlab/fork_rules.py ROWS.jsonl [ROWS2...] [--rule chase_dash] [--marks 10,30,60]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fork_patterns as fp  # noqa: E402


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def near_pos(r):
    s = r["sit"]
    return None if s["near_id"] is None else tuple(r["pos"][str(s["near_id"])][:2])


def rule_chase_dash(r, span=1):
    """Chasing (branch C) with the dash ready: the dash landing nearest the nearest enemy (ties: nearer home)."""
    s = r["sit"]
    if s["branch"] != "C" or not (s["dtype"] in fp.DASH1 and s["cd"][1] == 0):
        return None
    e = near_pos(r)
    c = [a for a in r["arms"] if a["label"]["kind"] == "dash" and a["label"].get("span", 1) == span]
    if not c or e is None:
        return None
    return min(c, key=lambda a: (cheb((a["label"]["x"], a["label"]["y"]), e), a["geo"].get("dh", 0)))


def rule_retreat_dash(r, span=1):
    """Retreating (R) with the dash ready: the dash landing farthest from the nearest enemy (ties: nearer home)."""
    s = r["sit"]
    if s["branch"] != "R" or not (s["dtype"] in fp.DASH1 and s["cd"][1] == 0):
        return None
    e = near_pos(r)
    c = [a for a in r["arms"] if a["label"]["kind"] == "dash" and a["label"].get("span", 1) == span]
    if not c or e is None:
        return None
    return min(c, key=lambda a: (-cheb((a["label"]["x"], a["label"]["y"]), e), a["geo"].get("dh", 0)))


def rule_attack_low(r, span=1):
    """Any branch with a basic attack legal: the attack on the lowest-health-share enemy."""
    c = [a for a in r["arms"] if a["label"]["kind"] == "attack" and a["label"].get("span", 1) == span]
    if not c:
        return None
    hp = lambda a: r["pos"][str(a["label"]["target"])][2] / r["pos"][str(a["label"]["target"])][3]
    return min(c, key=hp)


def rule_stun_near(r, span=1):
    """Any branch with a unit stun/damage cast legal on an enemy: the cast on the nearest."""
    c = [a for a in r["arms"] if a["label"]["kind"] == "cast_enemy" and a["label"].get("span", 1) == span]
    if not c:
        return None
    return next((a for a in c if a["label"]["target"] == r["sit"]["near_id"]), c[0])


def rule_chase_dash_any(r, span=1):
    """Chasing (C) with the dash ready: the mean of every dash that lands nearer the nearest enemy (see evaluate)."""
    s = r["sit"]
    if s["branch"] != "C" or not (s["dtype"] in fp.DASH1 and s["cd"][1] == 0):
        return None
    c = [a for a in r["arms"] if a["cls"].startswith("dash:toward") and a["label"].get("span", 1) == span]
    return c or None


RULES = {k[5:]: v for k, v in globals().items() if k.startswith("rule_")}


def evaluate(rows, rule, mark, key, span):
    items, same, fired = [], 0, 0
    for r in rows:
        a = RULES[rule](r, span)
        if a is None:
            continue
        fired += 1
        group = a if isinstance(a, list) else [a]  # a list: the rule is the mean of these arms
        if any(x["same_as_ocean"] for x in group):
            same += 1
            continue
        fv = fp.fork_values(r, mark, key)
        if fv is None:
            continue
        arms, V, ni, R = fv
        js = [i for i, x in enumerate(arms) if any(x["arm"] == g["arm"] for g in group)]
        if not js:
            continue
        items.append((r["src"] + "|" + r["game"], sum(sum(V[j]) / R for j in js) / len(js) - sum(V[ni]) / R))
    return fired, same, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", nargs="+")
    ap.add_argument("--rule", default=",".join(RULES))
    ap.add_argument("--marks", default="10,30,60")
    ap.add_argument("--keys", default="KD,CL,E")
    ap.add_argument("--span", type=int, default=1)
    a = ap.parse_args()
    sets = [(f, fp.load(f)) for f in a.rows]
    for rule in a.rule.split(","):
        print(f"\n== {rule} (span {a.span}): {RULES[rule].__doc__}")
        for f, rows in sets:
            for key in a.keys.split(","):
                cells = []
                for mk in a.marks.split(","):
                    fired, same, items = evaluate(rows, rule, mk, key, a.span)
                    m, lo, hi = fp.cluster_ci(items)
                    h = [[v for g, v in items if fp.half_game(g) == k] for k in (0, 1)]
                    hm = [sum(x) / len(x) if x else float("nan") for x in h]
                    cells.append(f"m{mk} {m:+.3f} [{lo:+.3f},{hi:+.3f}] ({hm[0]:+.3f}/{hm[1]:+.3f})" if m is not None else f"m{mk} -")
                print(f"  {Path(f).name:18s} {key:3s} fired {fired:4d} same {same:4d} n {len(items):4d}  " + "  ".join(cells))


if __name__ == "__main__":
    main()
