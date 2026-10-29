"""Pilot analysis for the emblem lab: are the logs right, do pairs carry more information per game than
independent games, and how large are emblem effects (so how many games the main run needs).

    py tools/emblab/pilot.py --lab pilot"""
import argparse, collections, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evehicle as ev  # noqa: E402

KAPPA = 5
CH = ev.CHAMPS


def jsonl(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def sig(x):
    return 1 / (1 + math.exp(-max(-30, min(30, x))))


def soft(g):
    a, b = g["wealth"]
    return sig(KAPPA * (a - b) / (a + b + 50))


def row_of(team, t):
    """The arm row of champion type t in a team (draft names in pick order)."""
    draft = t if t < 3 else 3 if t <= 4 else t - 1
    return 5 if t == 4 else team.index(CH[draft])


def solve(A, b):
    n = len(b)
    M = [A[i][:] + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c] / M[c][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def inverse_diag(A):
    """The diagonal of A's inverse, by one Gauss-Jordan pass."""
    n = len(A)
    M = [A[i][:] + [1.0 if j == i else 0.0 for j in range(n)] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        M[c] = [x / piv for x in M[c]]
        for r in range(n):
            if r != c and M[r][c]:
                f = M[r][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n + i] for i in range(n)]


def logistic(X, y, lam, iters=12):
    """Ridge logistic regression (soft targets allowed): coefficients and their standard errors."""
    p = len(X[0])
    th = [0.0] * p
    for _ in range(iters):
        g = [-lam[j] * th[j] for j in range(p)]
        H = [[0.0] * p for _ in range(p)]
        for x, t in zip(X, y):
            nz = [(j, v) for j, v in enumerate(x) if v]
            q = sig(sum(th[j] * v for j, v in nz))
            w = q * (1 - q)
            for j, v in nz:
                g[j] += (t - q) * v
                for k, u in nz:
                    H[j][k] += w * v * u
        for j in range(p):
            H[j][j] += lam[j]
        step = solve(H, g)
        th = [a + s for a, s in zip(th, step)]
        if max(map(abs, step)) < 1e-6:
            break
    return th, [math.sqrt(max(0.0, v)) for v in inverse_diag(H)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab", default="pilot")
    a = ap.parse_args()
    lab = Path(__file__).resolve().parents[2] / "replays" / "emblab" / a.lab
    G = [g for g in jsonl(lab / "games.jsonl") if "winner" in g and g.get("draft_ok") and "wealth" in g]
    D = jsonl(lab / "decisions.jsonl")
    by = collections.defaultdict(list)
    for d in D:
        by[d["id"]].append(d)
    print(f"{len(G)} games, {len(D)} decisions")

    # Logs: compliance, reach, fuel, stdout.
    c = collections.Counter()
    for d in D:
        c["forced bought" if d["arm"] >= 0 and d["chosen"] == d["arm"] else "forced NOT bought" if d["arm"] >= 0 else
          "passive owned" if d["arm"] == -2 else "model"] += 1
    print("decisions:", dict(c))
    champs = sum(len(g["A"]) + len(g["B"]) + g["A"].count("cassi_and_issac") + g["B"].count("cassi_and_issac") for g in G)
    reach = collections.Counter(d["k"] for d in D)
    print("reach by ordinal:", ", ".join(f"k{k} {reach[k] / champs:.2f}" for k in range(8)))
    print(f"out-of-fuel turns per team-game {sum(sum(g['oof']) for g in G) / len(G) / 2:.2f}; stdout max {max(max(g['stdout']) for g in G)}, "
          f"logs over 900k {sum(b > 900_000 for g in G for b in g['stdout'])}")

    # Pairs: identical before the flipped decision, and how often they still agree after.
    pairs = collections.defaultdict(list)
    for g in G:
        if "pair" in g:
            pairs[g["pair"]].append(g)
    pairs = [sorted(v, key=lambda g: g["vehicle"]) for v in pairs.values() if len(v) == 2]
    reached = prefix_ok = 0
    for o, f in pairs:
        fl = f["flip"]
        t = "AB".index(fl["side"])
        def at(g):
            return next((d for d in by[g["id"]] if d["team"] == t and d["k"] == fl["k"] and row_of(g[fl["side"]], d["type"]) == fl["row"]), None)
        do, df = at(o), at(f)
        if do and df:
            reached += 1
            before = lambda g, r: [(d["team"], d["type"], d["k"], d["round"], d["chosen"]) for d in by[g["id"]] if d["round"] < r]
            prefix_ok += before(o, do["round"]) == before(f, df["round"]) and do["round"] == df["round"]
    print(f"pairs {len(pairs)}: flipped decision reached in both {reached}, identical before it {prefix_ok}")
    # Independent same-map couples (the unpaired vehicle pairs) as the baseline for agreement.
    couples = collections.defaultdict(list)
    for g in G:
        if "pair" not in g:
            couples[(g["key"], g["vehicle"] // 2)].append(g)
    couples = [v for v in couples.values() if len(v) == 2]

    def agree(cs):
        w = sum(x["winner"] == y["winner"] for x, y in cs) / max(1, len(cs))
        sx = [soft(x) for x, _ in cs]
        sy = [soft(y) for _, y in cs]
        mx, my = sum(sx) / len(sx), sum(sy) / len(sy)
        cov = sum((p - mx) * (q - my) for p, q in zip(sx, sy))
        r = cov / math.sqrt(sum((p - mx) ** 2 for p in sx) * sum((q - my) ** 2 for q in sy))
        return w, r
    print("same winner / margin correlation: pairs %.3f / %.3f, independent same-map couples %.3f / %.3f" % (*agree(pairs), *agree(couples)))

    # Effects. Per team: the forced arms it was dealt at ordinals 0-2 (by the table: random, so unbiased whether
    # reached or not), by family; champions in the team soak up draft variance.
    fams = [f for f in range(len(ev.FAMILIES)) if ev.FAMILIES[f] != "greed"]
    K = 3
    cols = [("side",)] + [("champ", c) for c in range(len(CH))] + [("fam", k, f) for k in range(K) for f in fams]
    idx = {c: i for i, c in enumerate(cols)}

    def team_counts(g, s):
        v = collections.Counter()
        for c in g[s]:
            v[("champ", CH.index(c))] += 1
        for row in range(6):
            for k in range(K):
                arm = g[f"arms{s}"][row][k]
                if arm != ev.MODEL:
                    v[("fam", k, arm // 3)] += 1
        return v

    def design(games):
        X, yw, ys = [], [], []
        for g in games:
            ca, cb = team_counts(g, "A"), team_counts(g, "B")
            x = [0.0] * len(cols)
            x[0] = 1
            for key in set(ca) | set(cb):
                x[idx[key]] = ca[key] - cb[key]
            X.append(x)
            yw.append(1.0 if g["winner"] == 0 else 0.0)
            ys.append(soft(g))
        return X, yw, ys
    indep = [g for g in G if "pair" not in g] + [o for o, _ in pairs]  # one game of each pair: independent draws
    X, yw, ys = design(indep)
    lam = [0.01] + [1.0] * len(CH) + [1.0] * (len(cols) - 1 - len(CH))
    for name, y in (("win", yw), ("margin", ys)):
        th, se = logistic(X, y, lam)
        print(f"\nIndependent games ({len(indep)}), target {name}: forced family at ordinal k against the model's choice "
              f"(logit; x25 = win points near 50%)")
        for k in range(K):
            ests = [(ev.FAMILIES[f], th[idx[("fam", k, f)]], se[idx[("fam", k, f)]]) for f in fams]
            print(f"  k{k}: " + "  ".join(f"{n[:5]} {b:+.2f}±{s:.2f}" for n, b, s in ests))
            bs, ss = [b for _, b, _ in ests], [s for _, _, s in ests]
            mean = sum(bs) / len(bs)
            spread = sum((b - mean) ** 2 for b in bs) / (len(bs) - 1) - sum(s * s for s in ss) / len(ss)
            print(f"      mean {mean:+.3f}, between-family sd {math.sqrt(max(0, spread)):.3f}, typical se {sum(ss) / len(ss):.3f}")

    # Pairs: the flipped team's outcome difference, per unit of (new arm - old arm), against the same estimate
    # from independent games: information per game decides the design.
    def flip_effect(target):
        diffs = []
        for o, f in pairs:
            fl = f["flip"]
            if fl["k"] != 0:
                continue
            sign = 1 if fl["side"] == "A" else -1
            yo, yf = (soft(o), soft(f)) if target == "margin" else (float(o["winner"] == 0), float(f["winner"] == 0))
            d = sign * (yf - yo)
            if fl["old"] == ev.MODEL:
                diffs.append(d)            # model -> arm
            elif fl["new"] == ev.MODEL:
                diffs.append(-d)           # arm -> model, as model -> arm
        n = len(diffs)
        m = sum(diffs) / n
        sd = math.sqrt(sum((x - m) ** 2 for x in diffs) / (n - 1))
        return m, sd / math.sqrt(n), n

    for name, y in (("win", yw), ("margin", ys)):
        m, se, n = flip_effect(name)
        # Independent: one pooled 'forced at k0' coefficient on the same games, in probability units.
        cols1 = [0, *range(1, 1 + len(CH))]
        X1 = [[x[j] for j in cols1] + [sum(x[idx[("fam", 0, f)]] for f in fams)] for x in X]
        th, se1 = logistic(X1, y, [0.01] + [1.0] * len(CH) + [0.0])
        ind_eff, ind_se = th[-1] / 4, se1[-1] / 4
        info_pair = 1 / (se * se * 2 * n)
        info_ind = 1 / (ind_se * ind_se * len(indep))
        print(f"\nForced random arm at k0 instead of the model ({name}): pairs {m:+.4f}±{se:.4f} ({n} pairs), "
              f"independent {ind_eff:+.4f}±{ind_se:.4f} ({len(indep)} games); information per game pairs/independent "
              f"{info_pair / info_ind:.2f}")


if __name__ == "__main__":
    main()
