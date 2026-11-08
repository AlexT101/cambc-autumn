"""Paired estimate of CAND-vs-BASE against a BASE-vs-BASE mirror on the same (map, side).
Local games are deterministic, so the mirror game is CAND's exact counterfactual until its change first acts:
games where it never acts score d = 0 and add no noise.
usage: paired.py --cand DIR [DIR...] --mirror DIR [DIR...]   (batch dirs holding results.json)"""
import argparse, json, math, os, sys


def load(dirs):
    out = {}
    for d in dirs:
        try:
            r = json.load(open(os.path.join(d, "results.json")))
        except (OSError, ValueError):
            continue
        for m in r["matches"]:
            if "error" in m or "winner" not in m:
                continue
            out[(os.path.basename(os.path.realpath(m["map"])), tuple(m["order"]))] = (int(m["winner"] == 0), m.get("rounds"))
    return out


ap = argparse.ArgumentParser()
ap.add_argument("--cand", nargs="+", required=True)
ap.add_argument("--mirror", nargs="+", required=True)
a = ap.parse_args()
c, m = load(a.cand), load(a.mirror)
keys = [k for k in c if k in m]
n = len(keys)
if not n:
    sys.exit("no joined games")
d = [c[k][0] - m[k][0] for k in keys]
diff = [x for x in d if x]
wins, losses = sum(x > 0 for x in d), sum(x < 0 for x in d)
same_rounds = sum(c[k] == m[k] for k in keys)
mean = sum(d) / n
var = sum((x - mean) ** 2 for x in d) / max(n - 1, 1)
se = math.sqrt(var / n)
print(json.dumps({
    "joined": n, "identical_outcome_and_rounds": same_rounds, "flips": len(diff), "flip_wins": wins, "flip_losses": losses,
    "cand_wr": round(100 * sum(c[k][0] for k in keys) / n, 3), "mirror_wr": round(100 * sum(m[k][0] for k in keys) / n, 3),
    "delta_pts": round(100 * mean, 3), "ci95_pts": [round(100 * (mean - 1.96 * se), 3), round(100 * (mean + 1.96 * se), 3)],
    "diverged_games": n - same_rounds,
    "delta_on_diverged_pts": round(100 * sum(d) / max(n - same_rounds, 1), 3),
}))
