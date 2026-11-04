"""Compare osc_detect outputs: episode turns by kind, out-of-fuel turns, and a paired bootstrap CI against the first.

    py tools/replay/osc_compare.py REF_OUT CAND_OUT [CAND_OUT ...]

Each OUT is an osc_detect.py --out dir (run with --bridge-oof: an out-of-fuel turn prints no D line, and without it
splits its champion's run, so a bot with more of them shows fewer episodes). Games pair by map and side (the replay
name without its index), so run every bot on the same maps against the same opponent. The CI resamples games
(1,000 draws): diverged games make game-level noise far larger than a fuel-only pair's difference suggests.
"""
import json
import random
import re
import sys
from collections import Counter


def load(d):
    g = {}
    with open(f"{d}/games.tsv") as f:
        next(f)
        for line in f:
            c = line.rstrip("\n").split("\t")
            g[re.sub(r"^\d+-", "", c[0].rsplit("/", 1)[-1])] = (int(c[9]), json.loads(c[10].replace("'", '"')))
    return g


def main():
    dirs = sys.argv[1:]
    ds = [load(d) for d in dirs]
    names = [d.rstrip("/").rsplit("/", 1)[-1] for d in dirs]
    keys = sorted(set(ds[0]).intersection(*ds[1:]))
    order = Counter()
    for k in keys:
        order.update(ds[0][k][1])
    kinds = [k for k, _ in order.most_common()]

    def col(d, kind):
        if kind == "oof":
            return [d[k][0] for k in keys]
        if kind == "all":
            return [sum(d[k][1].values()) for k in keys]
        if kind == "all+oof":
            return [sum(d[k][1].values()) + d[k][0] for k in keys]
        return [d[k][1].get(kind, 0) for k in keys]

    print(f"{len(keys)} games in common\n")
    print("| kind | " + " | ".join(names) + " |\n|---|" + "---|" * len(names))
    for kind in kinds + ["all", "oof", "all+oof"]:
        r = sum(col(ds[0], kind))
        cells = [f"{r:,}"] + [f"{c:,} ({100 * (c - r) / max(r, 1):+.1f}%)" for c in (sum(col(d, kind)) for d in ds[1:])]
        print(f"| {kind} | " + " | ".join(cells) + " |")
    rng = random.Random(1)
    n = len(keys)
    draws = [Counter(rng.randrange(n) for _ in range(n)) for _ in range(1000)]
    print()
    for kind in ("all+oof", "all"):
        a = col(ds[0], kind)
        for name, d in zip(names[1:], ds[1:]):
            b = col(d, kind)
            r = sorted(100 * (sum(b[i] * w for i, w in c.items()) - sa) / sa
                       for c in draws for sa in [sum(a[i] * w for i, w in c.items())])
            print(f"{kind}: {name} vs {names[0]} {100 * (sum(b) - sum(a)) / sum(a):+.2f}% (95% CI {r[25]:+.2f} to {r[974]:+.2f})")


if __name__ == "__main__":
    main()
