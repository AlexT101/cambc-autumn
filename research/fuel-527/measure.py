"""Complete exhaustion counts; bootstrap whole maps, keeping their two sides together.

py research/fuel-527/measure.py bench BASE.json CAND.json
py research/fuel-527/measure.py release replays/ab/NAME/summary.json
"""
import collections
import json
import random
import re
import sys
from pathlib import Path


def bench(path):
    path = Path(path)
    counts = {}
    pending = None
    for line in path.with_name(path.stem + "-games").joinpath("run-batch.log").read_text().splitlines():
        if m := re.search(r"Out of fuel: A (\d+) B (\d+)", line):
            pending = tuple(map(int, m.groups()))
        elif pending is not None and "Replay: " in line:
            name = Path(line.split("Replay: ", 1)[1]).parent.name
            map_, side = name.rsplit("-", 1)
            counts[map_, side] = pending[side == "b"]
            pending = None
    data = json.loads(path.read_text())
    out = {}
    for g in data["games"]:
        assert "error" not in g, g
        key = g["map"], g["side"]
        shortcuts = sum(v for k, v in g["shortcuts"].items() if k != "out-of-fuel" and "SLOT" not in k)
        out[key] = [counts[key], shortcuts, sum(g["play"]), len(g["play"])]
    return out


def interval(rows, metrics):
    n = len(rows)
    sums = lambda ids: [sum(rows[i][j] for i in ids) for j in range(len(rows[0]))]
    totals = sums(range(n))
    rng = random.Random(527)
    samples = [metrics(sums([rng.randrange(n) for _ in range(n)])) for _ in range(2000)]
    point = metrics(totals)
    cis = []
    for j in range(len(point)):
        x = sorted(s[j] for s in samples)
        cis.append([x[50], x[1949]])
    return totals, point, cis


def main():
    if sys.argv[1] == "bench":
        a, b = bench(sys.argv[2]), bench(sys.argv[3])
        assert a.keys() == b.keys()
        grouped = collections.defaultdict(lambda: [0] * 8)
        for k in a:
            grouped[k[0]] = [x + y for x, y in zip(grouped[k[0]], a[k] + b[k])]
        rows = [grouped[k] for k in sorted(grouped)]

        def metrics(s):
            return [s[4] / s[0] - 1, s[5] / s[1] - 1,
                    (s[6] / s[7]) / (s[2] / s[3]) - 1,
                    (s[4] / s[7]) / (s[0] / s[3]) - 1,
                    (s[5] / s[7]) / (s[1] / s[3]) - 1]

        totals, point, cis = interval(rows, metrics)
        out = dict(games=len(a), maps=len(rows),
                   baseline=dict(zip(("oof", "shortcuts", "fuel", "turns"), totals[:4])),
                   candidate=dict(zip(("oof", "shortcuts", "fuel", "turns"), totals[4:])))
        names = ("oof", "shortcuts", "mean_fuel", "oof_per_turn", "shortcuts_per_turn")
    elif sys.argv[1] == "release":
        data = json.loads(Path(sys.argv[2]).read_text())
        assert data["release"] and data["errors"] == 0
        grouped = collections.defaultdict(lambda: [0, 0])
        for suite in data["suites"]:
            batch = json.loads(Path(suite["batch"]).joinpath("results.json").read_text())
            for game in batch["matches"]:
                assert "oof_turns" in game
                # run_batched stores these in bot order, independent of team A/B.
                c, r = game["oof_turns"]
                grouped[game["map"]][0] += r
                grouped[game["map"]][1] += c
        rows = [grouped[k] for k in sorted(grouped)]
        totals, point, cis = interval(rows, lambda s: [s[1] / s[0] - 1])
        assert totals == [data["oof"]["ref"][0], data["oof"]["cand"][0]]
        out = dict(games=data["games"], maps=len(rows), baseline_oof=totals[0], candidate_oof=totals[1],
                   win_pct=data["cand_win_pct"], win_ci95=data["ci95"], errors=data["errors"],
                   early_losses=data["early_losses"], handoff_failures=data["handoff_failures"],
                   capped_drafts=data["capped_drafts"])
        names = ("oof",)
    else:
        raise SystemExit(__doc__)
    out["change_pct"] = {name: dict(estimate=100 * value, ci95=[100 * v for v in ci])
                         for name, value, ci in zip(names, point, cis)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
