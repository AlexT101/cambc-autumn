"""Situation x action-class patterns in fork_regret.py rows: where a fixed alternative beats ocean's own action,
found on one half of the games and measured on the other half and on a second opponent's games.

    py tools/combatlab/fork_patterns.py --disc A.rows.jsonl:0 --test A.rows.jsonl:1 --test B.rows.jsonl \\
        [--mark 30] [--key CL] [--min-n 40] [--top 40] [--json out.json]

`FILE:H` keeps the forks of half H (fork_regret's map-hash half); a bare FILE keeps all.

Per fork, a class's gain is the mean over its arms and over the noise reps of the score, minus the `none` arm's
mean over reps; forks where an arm of the class is ocean's own action are left out of that class (the rule would
not change anything there). A pattern is (situation predicate, class); its mean gain carries no max-over-arms
selection, so a held-out estimate of it is unbiased. Per pattern: n forks, mean gain with a 95% bootstrap CI
over games (forks of one game are not independent), and the discovery estimate.
Also prints the noise floor: naive regret (best arm on rep 0 minus none), cross-fit regret (best arm on one rep,
scored on the others), and the replicate noise.
"""
import argparse
import json
import random
import statistics
from collections import defaultdict


def load(spec):
    path, _, half = spec.partition(":")
    rows = []
    for l in open(path):
        r = json.loads(l)
        if half == "" or r["half"] == int(half):
            rows.append(r)
    return rows


def base_cls(c):
    return c[:-2] if c.endswith("x3") else c


def fork_values(r, mark, key):
    arms = [a for a in r["arms"] if a["sc"].get(mark) and all(x is not None for x in a["sc"][mark])]
    if not arms:
        return None
    R = min(len(a["sc"][mark]) for a in arms)
    V = [[a["sc"][mark][k][key] for k in range(R)] for a in arms]
    ni = next((i for i, a in enumerate(arms) if a["cls"] == "none"), None)
    if ni is None:
        return None
    return arms, V, ni, R


def gains(r, mark, key):
    fv = fork_values(r, mark, key)
    if fv is None:
        return None
    arms, V, ni, R = fv
    nb = statistics.mean(V[ni])
    by = defaultdict(list)
    own = set()
    for a, v in zip(arms, V):
        if a["cls"] == "none":
            continue
        by[a["cls"]].append(statistics.mean(v) - nb)
        if a["same_as_ocean"]:
            own.add(a["cls"])
            own.add(a["cls"] + "x3")
    return {c: statistics.mean(g) for c, g in by.items() if c not in own and base_cls(c) not in own}


def regrets(r, mark, key):
    fv = fork_values(r, mark, key)
    if fv is None:
        return None
    arms, V, ni, R = fv
    v0 = [v[0] for v in V]
    naive = max(v0) - v0[ni]
    cf = None
    if R > 1:
        g = []
        for k in range(R):
            vk = [v[k] for v in V]
            b = max(range(len(V)), key=lambda i: (vk[i], i == ni))
            g.append(statistics.mean(V[b][j] - V[ni][j] for j in range(R) if j != k))
        cf = statistics.mean(g)
    noise = [V[ni][k] - V[ni][0] for k in range(1, R)]
    return naive, cf, noise


DASH1 = {"vesper", "vendetta", "issac", "ren", "hor"}  # dash in slot 1


def hp_b(h):
    return "low" if h < 0.4 else "mid" if h < 0.75 else "high"


def size_b(s):
    if s["e8"] == 0:
        return "none8"
    if s["e8"] == 1 and s["a8"] == 0:
        return "1v1"
    if s["e8"] >= s["a8"] + 2:
        return "outnumbered"
    if s["e8"] == s["a8"] + 1:
        return "even"
    return "outnumbering"


def dist_b(d):
    return "d<=2" if d <= 2 else "d3-4" if d <= 4 else "d5-6" if d <= 6 else "d7+"


def home_b(h):
    return "home<=6" if h <= 6 else "home7-15" if h <= 15 else "home16+"


def tags(r):
    s = r["sit"]
    b = s["branch"] if s["branch"] in "RCAFP" and s["branch"] else "o"
    t = {
        "br": "br=" + b,
        "hp": "hp=" + hp_b(s["hp"]),
        "size": "size=" + size_b(s),
        "dist": dist_b(s["d_enemy"]),
        "home": home_b(s["home"]),
        "rng": "ranged" if s["ranged"] else "melee",
        "type": "type=" + s["dtype"],
        "nearlow": "nearlow" if s["near_hp"] is not None and s["near_hp"] < 0.4 else "nearok",
        "hpadv": "hpadv" if s["near_hp"] is not None and s["hp"] > s["near_hp"] + 0.2 else "hpdis" if s["near_hp"] is not None and s["hp"] < s["near_hp"] - 0.2 else "hpeq",
        "carrier": "carrier" if s["gems"] >= 20 else "nobag",
        "ratio": "ratio<0.7" if s["hp_ratio"] < 0.7 else "ratio>1.4" if s["hp_ratio"] > 1.4 else "ratio~1",
        "danger": "danger" if s["hp"] < 0.5 and s["d_enemy"] <= 3 else "nodanger",
        "dash": "dashready" if s["dtype"] in DASH1 and s["cd"][1] == 0 else "nodash",
        "edash": "edashready" if s["near_type"] in DASH1 and s["near_cd"] and s["near_cd"][1] == 0 else "noedash",
        "ally": "ally4" if s["a4"] >= 1 else "noally4",
        "oc": "oc=" + r["ocean"].split(":")[0].split("+")[0] + (":" + r["ocean"].split(":")[1].split("+")[0] if ":" in r["ocean"] else "") + ("+hit" if "+hit" in r["ocean"] else ""),
    }
    return t


def preds(r):
    t = tags(r)
    out = ["all"] + list(t.values())
    keys = list(t)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            out.append(t[a] + "&" + t[b])
    return out


def half_game(gid):
    """A table key's game (src|game) -> its map-hash half, as fork_regret's."""
    import hashlib
    m = gid.split("|", 1)[1].split("#")[0]
    return int(hashlib.md5(m.encode()).hexdigest(), 16) % 2


def cluster_ci(items, n_boot=400, seed=1):
    """items: [(game, value)]; mean and 95% bootstrap CI resampling games."""
    by = defaultdict(list)
    for g, v in items:
        by[g].append(v)
    gs = list(by)
    if not gs:
        return None, None, None
    tot = sum(len(v) for v in by.values())
    mean = sum(sum(v) for v in by.values()) / tot
    rnd = random.Random(seed)
    ms = []
    for _ in range(n_boot):
        s = n = 0
        for _ in gs:
            v = by[gs[rnd.randrange(len(gs))]]
            s += sum(v)
            n += len(v)
        ms.append(s / n)
    ms.sort()
    return mean, ms[int(0.025 * n_boot)], ms[int(0.975 * n_boot) - 1]


def table(rows, mark, key):
    """(pred, cls) -> [(game, gain)]"""
    out = defaultdict(list)
    for r in rows:
        g = gains(r, mark, key)
        if not g:
            continue
        ps = preds(r)
        gid = r["src"] + "|" + r["game"]
        for c, v in g.items():
            for p in ps:
                out[(p, c)].append((gid, v))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disc", action="append", required=True)
    ap.add_argument("--test", action="append", default=[])
    ap.add_argument("--mark", default="30")
    ap.add_argument("--key", default="CL")
    ap.add_argument("--min-n", type=int, default=40)
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--json")
    a = ap.parse_args()
    disc = [r for s in a.disc for r in load(s)]
    tests = [(s, load(s)) for s in a.test]
    # Noise floor.
    for name, rs in [("disc", disc)] + tests:
        nv, cfv, nz = [], [], []
        for r in rs:
            x = regrets(r, a.mark, a.key)
            if x is None:
                continue
            nv.append(x[0])
            if x[1] is not None:
                cfv.append(x[1])
            nz += x[2]
        rms = (sum(v * v for v in nz) / len(nz)) ** 0.5 if nz else 0
        print(f"[{name}] mark {a.mark} {a.key}: {len(nv)} forks; naive regret {statistics.mean(nv):.3f}; cross-fit over reps "
              f"{statistics.mean(cfv) if cfv else float('nan'):.3f}; none-arm replicate noise rms {rms:.3f}, nonzero {sum(1 for v in nz if abs(v) > 1e-9) / max(1, len(nz)):.2f}")
    td = table(disc, a.mark, a.key)
    tt = [(s, table(rs, a.mark, a.key)) for s, rs in tests]
    n_forks = len(disc)
    cand = []
    for (p, c), items in td.items():
        if len(items) < a.min_n:
            continue
        m = sum(v for _, v in items) / len(items)
        cand.append((m * len(items) / n_forks, m, p, c, items))
    cand.sort(key=lambda x: -x[0])
    res = []
    print(f"\npatterns ranked by discovery mean gain x share of forks (mark {a.mark}, {a.key}); held-out columns are unbiased")
    print(f"{'pred':45s} {'class':28s} {'n':>5s} {'disc':>7s} " + " ".join(f"{'test' + str(i):>24s}" for i in range(len(tests))))
    for score, m, p, c, items in cand[: a.top]:
        cells = []
        rec = {"pred": p, "cls": c, "disc_n": len(items), "disc_mean": m, "tests": []}
        for s, t in tt:
            it = t.get((p, c), [])
            mean, lo, hi = cluster_ci(it)
            rec["tests"].append({"src": s, "n": len(it), "mean": mean, "lo": lo, "hi": hi})
            cells.append(f"{len(it):4d} {mean:+.3f} [{lo:+.3f},{hi:+.3f}]" if mean is not None else f"{'-':>24s}")
        res.append(rec)
        print(f"{p:45s} {c:28s} {len(items):5d} {m:+.3f} " + " ".join(cells))
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
