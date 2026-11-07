#!/usr/bin/env python3
"""Flips report: how flipping a fighter's first want_home or chase verdict compares with ocean's own, by rollout outcome.

    python3 tools/combatlab/flip_report.py RUN.jsonl[:TEAMS] [RUN_Y.jsonl:TEAMS] [--death 1.0] [--gem 0.01]

RUN.jsonl is `fastrunner scenario ... --lab --decisions --flip SPANS` output; TEAMS (0, 1 or 01, default 01) are the
teams whose fighters' flips count. Gains are alt_report.py's reward differences (flipped rollout minus rollout 0) from
the flipped fighter's team side. A chase flip applied only where the fighter's decision at the flip's round took the
forced verdict (a forced chase with no target stays 0); a want_home flip always applies. With a second run (the same
frames against another opponent), flips present in both are compared: their gains' correlation (against a shuffled
baseline), and how a flip clearly better in one run does in the other.
"""
import argparse
import collections
import json
import math
import random
import statistics
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from alt_report import reward  # noqa: E402


def load(path, teams, death, gem):
    """{(scenario, fighter, what, span): (gain, applied, from, to)}"""
    base, rows = {}, []
    for line in open(path):
        r = json.loads(line)
        if "fighters" not in r or "flip" not in r:
            continue
        if r["flip"].get("k") == 0:
            base[r["id"]] = r
        else:
            rows.append(r)
    out = {}
    for r in rows:
        b = base.get(r["id"])
        if b is None:
            continue
        fl = r["flip"]
        f = next(x for x in r["fighters"] if x["id"] == fl["fighter"])
        if str(f["team"]) not in teams:
            continue
        applied = True
        if fl["what"] == "chase":
            d = next((d for d in f.get("decisions", []) if d["r"] == fl["round"]), None)
            applied = d is not None and d["chase"] == fl["to"]
        g = reward(r, f["team"], death, gem) - reward(b, f["team"], death, gem)
        out[(r["id"], fl["fighter"], fl["what"], fl["span"])] = (g, applied, fl["from"], fl["to"])
    return out


def corr(xs, ys):
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("x")
    ap.add_argument("y", nargs="?")
    ap.add_argument("--death", type=float, default=1.0)
    ap.add_argument("--gem", type=float, default=0.01)
    ap.add_argument("--margin", type=float, default=0.25)
    a = ap.parse_args()
    split = lambda s: s.rsplit(":", 1) if ":" in s.rsplit("/", 1)[-1] else (s, "01")
    px, tx = split(a.x)
    X = load(px, tx, a.death, a.gem)
    groups = collections.defaultdict(list)
    for (sid, fid, what, span), (g, applied, fr, to) in X.items():
        if applied:
            groups[(what, f"{fr}->{to}", span)].append(g)
    print(f"{len(X)} flips, {sum(v[1] for v in X.values())} applied")
    print("what   verdict span      n   mean gain  better  worse  clearly better  clearly worse")
    for k in sorted(groups):
        v = groups[k]
        m = a.margin
        print(f"{k[0]:6s} {k[1]:7s} {k[2]:4d} {len(v):6d}   {statistics.fmean(v):+.3f}    {sum(x > 0 for x in v) / len(v):5.0%}  {sum(x < 0 for x in v) / len(v):5.0%}"
              f"  {sum(x > m for x in v) / len(v):13.0%}  {sum(x < -m for x in v) / len(v):12.0%}")
    if not a.y:
        return
    py, ty = split(a.y)
    Y = load(py, ty, a.death, a.gem)
    same = [k for k in X if k in Y and X[k][1] and Y[k][1] and X[k][2] == Y[k][2]]
    print(f"\nin both runs, applied in both, ocean's same verdict: {len(same)}")
    by = collections.defaultdict(list)
    for k in same:
        by[(k[2], X[k][2], k[3])].append((X[k][0], Y[k][0]))
    rng = random.Random(1)
    for k in sorted(by):
        ps = by[k]
        if len(ps) < 30:
            continue
        xs, ys = [p[0] for p in ps], [p[1] for p in ps]
        ysh = ys[:]
        rng.shuffle(ysh)
        clear = [y for x, y in ps if x > a.margin]
        tail = (f"; clearly better in X: {len(clear)}, in Y mean {statistics.fmean(clear):+.3f}, better {sum(y > 0 for y in clear) / len(clear):.0%}"
                if clear else "")
        print(f"  {k[0]:6s} from {k[1]} span {k[2]:2d}: n {len(ps):5d}, corr {corr(xs, ys):.3f} (shuffled {corr(xs, ysh):.3f}){tail}")


if __name__ == "__main__":
    main()
