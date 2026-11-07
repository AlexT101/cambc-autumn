#!/usr/bin/env python3
"""Do alternatives' gains over ocean's choice replicate across opponents?

    python3 tools/combatlab/alt_replicate.py RUN_X.jsonl:TEAMS RUN_Y.jsonl:TEAMS [--margin 0.25] [--bot-team ...]

Each argument is a `scenario --lab --decisions --alt K` output and the teams whose decisions to use from it (0, 1 or
01), e.g. oo.jsonl:01 oa.jsonl:0 compares team A's ocean decisions against ocean (oo) with the same decisions
against astraeus (oa). A decision is (scenario, fighter); it is compared only where ocean's own choice is the same
move in both runs. Alternatives are matched by the move (end tile, enemies removed, cast kept), not by rank. Gains
are reward differences from the deciding team's side (alt_report.py's reward).
"""
import argparse
import json
import math
import random
import statistics
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from alt_report import reward  # noqa: E402


def key(choice):
    return (choice["x"], choice["y"], choice["removed"], bool(choice["keep"]))


def load(path, teams, death, gem):
    base, alts = {}, {}
    for line in open(path):
        r = json.loads(line)
        if "fighters" not in r:
            continue
        a = r.get("alt") or {}
        if a.get("k", 0) == 0:
            base[r["id"]] = r
        else:
            alts.setdefault((r["id"], a["fighter"]), []).append(r)
    out = {}
    for (sid, fid), rs in alts.items():
        b = base.get(sid)
        if b is None:
            continue
        team = next(f["team"] for f in b["fighters"] if f["id"] == fid)
        if str(team) not in teams:
            continue
        first = ((b.get("alt") or {}).get("first") or {}).get(str(fid))
        if not first or not first.get("choice"):
            continue
        r0 = reward(b, team, death, gem)
        gains = {}
        for r in rs:
            c = r["alt"].get("choice")
            if c:
                gains[key(c)] = reward(r, team, death, gem) - r0
        out[(sid, fid)] = (key(first["choice"]), gains)
    return out


def corr(xs, ys):
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("x")
    ap.add_argument("y")
    ap.add_argument("--margin", type=float, default=0.25)
    ap.add_argument("--death", type=float, default=1.0)
    ap.add_argument("--gem", type=float, default=0.01)
    a = ap.parse_args()
    px, tx = a.x.rsplit(":", 1)
    py, ty = a.y.rsplit(":", 1)
    X, Y = load(px, tx, a.death, a.gem), load(py, ty, a.death, a.gem)
    common = [k for k in X if k in Y]
    same = [k for k in common if X[k][0] == Y[k][0]]
    pairs, decisions = [], []
    for k in same:
        gx, gy = X[k][1], Y[k][1]
        moves = [m for m in gx if m in gy]
        if moves:
            decisions.append((k, [(gx[m], gy[m]) for m in moves]))
            pairs += [(gx[m], gy[m]) for m in moves]
    print(f"decisions: {len(X)} in X, {len(Y)} in Y, {len(common)} in both, {len(same)} with ocean's same choice, "
          f"{len(decisions)} with a shared alternative; {len(pairs)} shared alternatives")
    if not pairs:
        return
    xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
    print(f"gain correlation across opponents: {corr(xs, ys):.3f}  (mean gain X {statistics.fmean(xs):+.3f}, Y {statistics.fmean(ys):+.3f})")
    # Shuffled baseline: pair each X gain with a Y gain of another decision.
    rng = random.Random(1)
    ysh = ys[:]
    rng.shuffle(ysh)
    print(f"shuffled baseline correlation: {corr(xs, ysh):.3f}")
    m = a.margin
    clear = [(x, y) for x, y in pairs if x > m]
    base_rate = sum(y > m for y in ys) / len(ys)
    if clear:
        print(f"alternatives clearly better in X (> {m}): {len(clear)}; of those clearly better in Y: "
              f"{sum(y > m for _, y in clear) / len(clear):.0%} (base rate in Y {base_rate:.0%}); better at all in Y: "
              f"{sum(y > 0 for _, y in clear) / len(clear):.0%} (base {sum(y > 0 for y in ys) / len(ys):.0%}); mean Y gain {statistics.fmean(y for _, y in clear):+.3f}")
    # Per decision: X's best alternative, if clearly better, against ocean's choice in Y.
    best = []
    for _, ps in decisions:
        bx, by = max(ps, key=lambda p: p[0])
        if bx > m:
            best.append(by)
    if best:
        print(f"decisions whose best alternative in X is clearly better: {len(best)} of {len(decisions)}; that alternative in Y: "
              f"mean gain {statistics.fmean(best):+.3f}, better {sum(b > 0 for b in best) / len(best):.0%}, worse {sum(b < 0 for b in best) / len(best):.0%}")


if __name__ == "__main__":
    main()
