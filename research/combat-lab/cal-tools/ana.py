"""Calibration tables from collect.py rows.  python3 ana.py ROWS.jsonl.gz [section...]"""
import gzip, json, math, sys
from collections import defaultdict

rows = [json.loads(l) for l in gzip.open(sys.argv[1], "rt")]
sections = sys.argv[2:] or ["overview", "rd", "stay", "members", "focus"]
LEAVE = set("RK")


def mbin(m):
    edges = [-3, -1.5, -1, -0.5, -0.25, -0.1, 0, 0.1, 0.25, 0.5, 1, 1.5, 3]
    if m <= -3:
        return "<=-3"
    if m >= 3:
        return ">=3"
    for a, b in zip(edges, edges[1:]):
        if a <= m < b if m < 0 else a < m <= b:
            return f"{a:+.2f}..{b:+.2f}"
    return "?"


ORDER = ["<=-3"] + [f"{a:+.2f}..{b:+.2f}" for a, b in zip([-3, -1.5, -1, -0.5, -0.25, -0.1, 0, 0.1, 0.25, 0.5, 1, 1.5], [-1.5, -1, -0.5, -0.25, -0.1, 0, 0.1, 0.25, 0.5, 1, 1.5, 3])] + [">=3"]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def se(xs):
    xs = list(xs)
    n = len(xs)
    if n < 2:
        return float("nan")
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n)


def bodies(d, k=10):
    return d[f"theirs_dead{k}"] - d[f"ours_dead{k}"]


def table(rs, key, title, k=10):
    g = defaultdict(list)
    for d in rs:
        g[key(d)].append(d)
    print(f"\n## {title}")
    print(f"{'bin':16} {'n':>6} {'lost%':>6} {'leave%':>6} {'eng%':>5} {'meDie':>6} {'thDie':>6} {'bodies':>7} {'+-':>5} {'1stOurs':>7} {'1stTheirs':>9} {'ours5':>6} {'theirs5':>7}")
    keys = sorted(g, key=lambda b: ORDER.index(b) if b in ORDER else str(b))
    for b in keys:
        x = g[b]
        n = len(x)
        if n < 20:
            continue
        print(f"{str(b):16} {n:6} {100*mean(d['verdict'] for d in x):6.1f} {100*mean(d['dec'] in LEAVE for d in x):6.1f} "
              f"{100*mean(d['mine3']>0 for d in x):5.1f} {100*mean(d[f'me_dies{k}'] for d in x):6.1f} "
              f"{100*mean(d[f'theirs_dead{k}']>0 for d in x):6.1f} {mean(bodies(d,k) for d in x):+7.3f} {1.96*se(bodies(d,k) for d in x):5.3f} "
              f"{100*mean(d['first']=='ours' for d in x):7.1f} {100*mean(d['first']=='theirs' for d in x):9.1f} {mean(d['ours5'] for d in x):6.0f} {mean(d['theirs5'] for d in x):7.0f}")


def nunseen(d):
    return sum(1 for e in d["enemies"] if not e["vis"])


def nwalk(d):
    return sum(1 for e in d["enemies"] if e["arr"] > 0)


CS = [d for d in rows if d["tag"] == "CS"]
CC = [d for d in rows if d["tag"] == "CC"]
print(f"{len(CS)} stand rows, {len(CC)} chase rows, {len({d['game'] for d in rows})} games")
if "overview" in sections:
    for name, rs in (("stand", CS), ("chase", CC)):
        print(f"\n# {name}: verdict lost {100*mean(d['verdict'] for d in rs):.1f}%, v1 mismatch {sum(d['v1']!=d['verdict'] for d in rs)}")
        from collections import Counter
        print(" decisions:", Counter(d["dec"] for d in rs).most_common(12))
        print(" lost by decision:", {k: f"{100*mean(d['verdict'] for d in rs if d['dec']==k):.0f}%" for k, _ in Counter(d['dec'] for d in rs).most_common(8)})
if "rd" in sections:
    table(CS, lambda d: mbin(d["m"]), "stand verdicts by margin (log2 our-health factor to flip; >0 lost)")
    table(CS, lambda d: (mbin(d["m"]), "leave" if d["dec"] in LEAVE else "stay"), "stand by margin and action")
    table(CC, lambda d: mbin(d["m"]), "chase candidates by margin")
    table(CC, lambda d: (mbin(d["m"]), "chase" if d["dec"] == "C" else "no"), "chase by margin and chase taken")
if "stay" in sections:
    near = [d for d in CS if abs(d["m"]) <= 0.5]
    table(near, lambda d: ("lost" if d["verdict"] else "won", "hp>=.9" if d["hp"] >= 0.9 * d["mhp"] else "hp<.9"), "stand |m|<=0.5 by verdict, own health")
    table(near, lambda d: ("lost" if d["verdict"] else "won", f"{len(d['allies'])}v{len(d['enemies'])}"), "stand |m|<=0.5 by verdict, roster")
    table(near, lambda d: ("lost" if d["verdict"] else "won", "unseen" if nunseen(d) else "all seen"), "stand |m|<=0.5 by unseen")
    table(near, lambda d: ("lost" if d["verdict"] else "won", "walkers" if nwalk(d) else "no walkers"), "stand |m|<=0.5 by walkers")


def rd(rs, title, outcome, width=0.25):
    """Local linear fits on each side of m=0 within `width`: the jump stay(won) - leave(lost) at the boundary."""
    def fit(xs):
        n = len(xs)
        if n < 10:
            return float("nan"), float("nan")
        mx = sum(x for x, _ in xs) / n
        my = sum(y for _, y in xs) / n
        sxx = sum((x - mx) ** 2 for x, _ in xs)
        b = sum((x - mx) * (y - my) for x, y in xs) / sxx if sxx else 0
        a = my - b * mx
        res = [y - (a + b * x) for x, y in xs]
        s2 = sum(r * r for r in res) / max(1, n - 2)
        # variance of intercept at x=0
        va = s2 * (1 / n + mx * mx / sxx) if sxx else s2 / n
        return a, math.sqrt(va)
    won = [(d["m"], outcome(d)) for d in rs if -width <= d["m"] < 0]
    lost = [(d["m"], outcome(d)) for d in rs if 0 < d["m"] <= width]
    a0, s0 = fit(won)
    a1, s1 = fit(lost)
    print(f"  {title:42} won-side {a0:+.4f} (n {len(won)})  lost-side {a1:+.4f} (n {len(lost)})  jump won-lost {a0-a1:+.4f} +- {1.96*math.sqrt(s0*s0+s1*s1):.4f}")


if "jump" in sections:
    for name, rs in (("stand", CS), ("chase", CC)):
        for w in (0.25, 0.5):
            print(f"\n# RD at m=0, {name}, bandwidth {w}")
            rd(rs, "bodies10", lambda d: bodies(d), w)
            rd(rs, "bodies20", lambda d: bodies(d, 20), w)
            rd(rs, "me_dies10", lambda d: d["me_dies10"], w)
            rd(rs, "theirs_dead10>0", lambda d: int(d["theirs_dead10"] > 0), w)
            rd(rs, "won_game", lambda d: d["won_game"], w)
if "members" in sections:
    print("\n## roster members: share that hit within arrival+1 rounds (stays only: our champion did not leave)")
    stays = [d for d in CS if d["dec"] not in LEAVE]
    g = defaultdict(list)
    for d in stays:
        for e in d["enemies"]:
            arr = min(e["arr"], 4)
            g[("enemy", "seen" if e["vis"] else "unseen", arr)].append(e["hit"] <= arr + 1)
        for a in d["allies"]:
            if a["id"] == d["me"]:
                continue
            g[("ally", "", min(a["arr"], 4))].append(a["hit"] <= a["arr"] + 1)
    for k in sorted(g):
        print(f"  {str(k):28} n {len(g[k]):7}  hit by arr+1: {100*mean(g[k]):5.1f}%")


import random


def boot_rd(rs, outcome, width, B=200):
    """RD jump with a bootstrap over games (rows within a game are correlated)."""
    by = defaultdict(list)
    for d in rs:
        if -width <= d["m"] <= width and d["m"] != 0:
            by[d["game"]].append((d["m"], outcome(d)))
    games = list(by)

    def jump(sample):
        won = [x for g in sample for x in by[g] if x[0] < 0]
        lost = [x for g in sample for x in by[g] if x[0] > 0]

        def fit(xs):
            n = len(xs)
            mx = sum(x for x, _ in xs) / n
            my = sum(y for _, y in xs) / n
            sxx = sum((x - mx) ** 2 for x, _ in xs)
            b = sum((x - mx) * (y - my) for x, y in xs) / sxx if sxx else 0
            return my - b * mx
        return fit(won) - fit(lost), sum(y for _, y in won) / len(won) - sum(y for _, y in lost) / len(lost)
    j, jm = jump(games)
    rng = random.Random(1)
    bs = sorted(jump([rng.choice(games) for _ in games]) for _ in range(B))
    lin = sorted(b[0] for b in bs)
    mn = sorted(b[1] for b in bs)
    return j, lin[int(0.025 * B)], lin[int(0.975 * B)], jm, mn[int(0.025 * B)], mn[int(0.975 * B)]


if "bjump" in sections:
    outs = [("bodies10", lambda d: bodies(d)), ("bodies20", lambda d: bodies(d, 20)), ("me_dies10", lambda d: d["me_dies10"]),
            ("theirs_dead10>0", lambda d: int(d["theirs_dead10"] > 0)), ("won_game", lambda d: d["won_game"])]
    for name, rs in (("stand", CS), ("chase", CC)):
        for w in (0.25, 0.5):
            print(f"\n# RD jump won(stay/chase) - lost at m=0, {name}, bandwidth {w}, 95% bootstrap over games")
            for t, f in outs:
                j, lo, hi, jm, mlo, mhi = boot_rd(rs, f, w)
                print(f"  {t:18} local-linear {j:+.4f} ({lo:+.4f}..{hi:+.4f})   difference of means {jm:+.4f} ({mlo:+.4f}..{mhi:+.4f})")

if "calib" in sections:
    print("\n## P(our side loses a champion first | someone died within 10), by margin; stays = our champion did not leave this turn")
    for name, rs in (("stand", CS), ("chase", CC)):
        g = defaultdict(list)
        for d in rs:
            if d["first"] == "none":
                continue
            act = ("leave" if d["dec"] in LEAVE else "stay") if name == "stand" else ("chase" if d["dec"] == "C" else "other")
            g[(mbin(d["m"]), act)].append(d["first"] == "ours")
        print(f"# {name}")
        for b in ORDER:
            parts = []
            for act in (("stay", "leave") if name == "stand" else ("chase", "other")):
                x = g.get((b, act), [])
                parts.append(f"{act} {100*mean(x):5.1f}% of {len(x):5}" if len(x) >= 20 else f"{act}    -  of {len(x):5}")
            print(f"  {b:14}  " + "   ".join(parts))

if "pair" in sections:
    idx = {(d["game"], d["team"], d["r"], d["me"]): d for d in CS}
    g = defaultdict(list)
    for d in CS:
        for e in d["enemies"]:
            if not e["vis"]:
                continue
            o = idx.get((d["game"], 1 - d["team"], d["r"], e["id"])) or idx.get((d["game"], 1 - d["team"], d["r"] + 1, e["id"]))
            if not o or d["me"] not in {x["id"] for x in o["enemies"]}:
                continue
            g[("we lost" if d["verdict"] else "we won", "they lost" if o["verdict"] else "they won")].append((d, o))
            break
    print("\n## stand verdicts paired with the enemy's stand verdict on the same contact (one enemy each)")
    tot = sum(len(v) for v in g.values())
    for k in sorted(g):
        v = g[k]
        print(f"  {k[0]:8} / {k[1]:9}: {len(v):6} ({100*len(v)/tot:4.1f}%)  our first death {100*mean(d['first']=='ours' for d,_ in v):5.1f}%  theirs first {100*mean(d['first']=='theirs' for d,_ in v):5.1f}%  bodies {mean(bodies(d) for d,_ in v):+.3f}")
