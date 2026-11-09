#!/usr/bin/env python3
"""Analyse fgparse.py output. usage: fgan.py A.jsonl [B.jsonl ...]"""
import sys, json, collections, statistics as st

ORDER = [0, 1, 2, 3, 4, 5, 6, 39, 7, 8, 9, 42, 10, 11, 36, 12, 37, 38, 13, 14]
STAGE = {1: "pre-retreat decide", 2: "retreat: kill/attack", 3: "retreat: dash/escape branch", 4: "retreat: reset",
         5: "retreat: flee/rs entry", 6: "rs: avoid checks", 39: "rs: plan build", 7: "rs: add/HomeWalk/pricing",
         8: "rs: tries", 9: "after move: retreat tail", 42: "after move: retreat tail", 10: "after move: act tail", 11: "after move: act tail",
         36: "after move: recall feint", 12: "after move: turn order", 37: "after move: turn order", 38: "after move: play_turn tail",
         13: "after move: main tail", 14: "after move: main tail", 0: "before decide"}


def pct(xs, q):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def summ(name, xs):
    if not xs:
        return f"{name}: n=0"
    return f"{name}: n={len(xs)} mean={st.mean(xs)/1000:.1f}k p50={pct(xs,.5)/1000:.1f}k p90={pct(xs,.9)/1000:.1f}k p99={pct(xs,.99)/1000:.1f}k max={max(xs)/1000:.1f}k"


def builds(v):
    out = []
    for k in range(min(3, v[15])):
        out.append(dict(ask=v[16 + 4 * k], cost=v[17 + 4 * k], st=v[18 + 4 * k], who=v[19 + 4 * k]))
    return out


for path in sys.argv[1:]:
    rows = [r for r in (json.loads(l) for l in open(path)) if len(r["v"]) == 47]
    fg = [r for r in rows if r["k"] == "FG"]
    fgo = [r for r in rows if r["k"] == "FGO" and r["r"] > 1]
    games = len({r["g"] for r in rows})
    print(f"==== {path}: {games} games with lines, finished retreat turns {len(fg)}, OOF turns (r>1) {len(fgo)}, of them in retreat {sum(1 for r in fgo if r['v'][31])}")
    # finished retreat turns
    nb = collections.Counter()
    for r in fg:
        b = builds(r["v"])
        nb[(len(b), tuple(x["st"] for x in b))] += 1
    print(" builds per finished retreat turn (count, statuses 1 gated 2 active 3 inactive):", nb.most_common(10))
    act = [r for r in fg if any(x["st"] == 2 for x in builds(r["v"]))]
    gated = [r for r in fg if builds(r["v"]) and builds(r["v"])[0]["st"] == 1]
    v = lambda r, i: r["v"][i]
    print(" " + summ("turn start->decide (pre)", [v(r, 0) - v(r, 1) for r in fg]))
    print(" " + summ("decide->retreat entry", [v(r, 1) - v(r, 2) for r in fg]))
    print(" " + summ("retreat()", [v(r, 2) - v(r, 10) for r in fg]))
    print(" " + summ("retreat end->act end", [v(r, 10) - v(r, 12) for r in fg]))
    print(" " + summ("set_turn_order", [v(r, 37) - v(r, 38) for r in fg if v(r, 38)]))
    print(" " + summ("turn start->play_turn end (excl queue)", [v(r, 0) - v(r, 13) for r in fg]))
    for nm, sel in (("with an active build", act), ("first ask gated", gated)):
        print(f" -- {nm}: {len(sel)}")
        print("   " + summ("fuel at first ask", [builds(r["v"])[0]["ask"] for r in sel]))
        print("   " + summ("build cost (all builds)", [sum(x["cost"] for x in builds(r["v"]) if x["st"] == 2) for r in sel]))
        print("   " + summ("slack cost", [v(r, 30) for r in sel]))
        rest = lambda r, end: builds(r["v"])[0]["ask"] - v(r, end) - sum(x["cost"] for x in builds(r["v"])) - v(r, 30)
        print("   " + summ("after first ask to retreat end, less plan", [rest(r, 10) for r in sel]))
        print("   " + summ("after first ask to act end, less plan", [rest(r, 12) for r in sel]))
        print("   " + summ("after first ask to play_turn end, less plan", [rest(r, 13) for r in sel]))
        print("   " + summ("rs pricing segment (7->8)", [v(r, 7) - v(r, 8) for r in sel if v(r, 8)]))
        print("   " + summ("fuel left at play_turn end", [v(r, 13) for r in sel]))
        print("   asker of first ask:", collections.Counter(builds(r["v"])[0]["who"] for r in sel))
    # By first-ask fuel bucket: how much was left at play_turn end
    print(" -- active first build, by fuel at ask: n, left at act end p10/p50, share left < 5k at act end")
    bk = collections.defaultdict(list)
    for r in act:
        a = builds(r["v"])[0]["ask"]
        bk[a // 10000 * 10].append(v(r, 12))
    for k in sorted(bk):
        xs = bk[k]
        print(f"   ask {k}-{k+10}k: n={len(xs)} p10={pct(xs,.1)/1000:.1f}k p50={pct(xs,.5)/1000:.1f}k <5k={sum(x<5000 for x in xs)/len(xs):.2%}")
    # OOF turns
    o = [r for r in fgo if r["v"][31]]
    print(f" -- OOF turns in retreat: {len(o)} (all OOF r>1: {len(fgo)})")
    last = collections.Counter(STAGE.get(r["v"][35], str(r["v"][35])) for r in o)
    for k, n in last.most_common():
        print(f"   last checkpoint {k}: {n}")
    ob = collections.Counter()
    for r in o:
        b = builds(r["v"])
        ob[(len(b), tuple(x["st"] for x in b))] += 1
    print("   builds:", ob.most_common(8))
    ab = [builds(r["v"])[0]["ask"] for r in o if builds(r["v"])]
    print("   " + summ("fuel at first ask (OOF)", ab))
    print("   " + summ("turn start fuel (OOF)", [r["v"][0] for r in o]))
    print("   " + summ("decide start (OOF)", [r["v"][1] for r in o]))
    print("   " + summ("retreat entry fuel (OOF)", [r["v"][2] for r in o]))
    non = [r for r in fgo if not r["v"][31]]
    print("   non-retreat OOF phases:", collections.Counter(r.get("ph") for r in non).most_common(6))
