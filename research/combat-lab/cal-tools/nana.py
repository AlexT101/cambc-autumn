"""Fast tables from flat.py's npz, game-clustered (Poisson bootstrap over games)."""
import sys
import numpy as np

Z = np.load(sys.argv[1])
D = {k: Z[k] for k in Z.files}
decs = list(D["decs"])
types = list(D["types"])
LEAVE = np.isin(D["dec"], [decs.index("R"), decs.index("K")])
CH = D["dec"] == decs.index("C")
G = D["game"]
NG = G.max() + 1
rng = np.random.default_rng(1)
W = rng.poisson(1.0, size=(200, NG)).astype(np.float64)
bodies10 = (D["td10"] - D["od10"]).astype(float)
bodies20 = (D["td20"] - D["od20"]).astype(float)
stand = D["tag"] == 0
chase = D["tag"] == 1


def wmean(mask, y):
    """mean and 95% bootstrap CI of y over rows in mask, clustered by game."""
    g = G[mask]
    s = np.bincount(g, weights=y[mask], minlength=NG)
    n = np.bincount(g, minlength=NG).astype(float)
    est = s.sum() / max(n.sum(), 1)
    bs = (W @ s) / np.maximum(W @ n, 1)
    return est, np.percentile(bs, 2.5), np.percentile(bs, 97.5), int(n.sum())


def diff(m1, m2, y):
    g1, g2 = G[m1], G[m2]
    s1 = np.bincount(g1, weights=y[m1], minlength=NG); n1 = np.bincount(g1, minlength=NG).astype(float)
    s2 = np.bincount(g2, weights=y[m2], minlength=NG); n2 = np.bincount(g2, minlength=NG).astype(float)
    est = s1.sum() / n1.sum() - s2.sum() / n2.sum()
    bs = (W @ s1) / (W @ n1) - (W @ s2) / (W @ n2)
    return est, np.percentile(bs, 2.5), np.percentile(bs, 97.5), int(n1.sum()), int(n2.sum())


def rdjump(base, y, w):
    """Local linear jump at m=0: won side (m<0) intercept minus lost side (m>0) intercept, bootstrap by game."""
    m = D["m"].astype(float)

    def inter(mask, wts):
        x, yy, ww = m[mask], y[mask], wts[G[mask]]
        sw = ww.sum(); mx = (ww * x).sum() / sw; my = (ww * yy).sum() / sw
        sxx = (ww * (x - mx) ** 2).sum()
        b = (ww * (x - mx) * (yy - my)).sum() / sxx
        return my - b * mx
    won = base & (m < 0) & (m >= -w)
    lost = base & (m > 0) & (m <= w)
    one = np.ones(NG)
    est = inter(won, one) - inter(lost, one)
    bs = [inter(won, W[i]) - inter(lost, W[i]) for i in range(100)]
    return est, np.percentile(bs, 2.5), np.percentile(bs, 97.5), int(won.sum()), int(lost.sum())


def fmt(t):
    return f"{t[0]:+.4f} ({t[1]:+.4f}..{t[2]:+.4f})"


EDGES = [-99, -3, -1.5, -1, -0.5, -0.25, -0.1, 0, 0.1, 0.25, 0.5, 1, 1.5, 3, 99]


def bins(mask, title, cols):
    m = D["m"]
    print(f"\n## {title}")
    print(f"{'margin':14} {'n':>8} " + " ".join(f"{c[0]:>24}" for c in cols))
    for a, b in zip(EDGES, EDGES[1:]):
        sel = mask & ((m > a) & (m <= b) if b <= 0 else (m > a) & (m <= b)) if a < 0 else mask & (m > a) & (m <= b)
        if a < 0 <= b:
            sel = mask & (m > a) & (m < 0)
        if a == 0:
            sel = mask & (m > 0) & (m <= b)
        n = int(sel.sum())
        if n < 50:
            continue
        print(f"{a:+.2f}..{b:+.2f} {n:8} " + " ".join(f"{fmt(wmean(sel, c[1](sel))):>24}" if False else f"{wmean(sel, c[1])[0]:24.4f}" for c in cols))


sections = sys.argv[2:] or ["all"]
first_ours = (D["first"] == 1).astype(float)
first_theirs = (D["first"] == 2).astype(float)
md10 = D["md10"].astype(float)
th10 = (D["td10"] > 0).astype(float)
won = D["won"].astype(float)
print(f"rows {len(G)}, games {NG}, stand {stand.sum()}, chase {chase.sum()}")

if "calib" in sections or "all" in sections:
    for name, base in (("stand", stand), ("chase", chase)):
        cols = [("bodies10", bodies10), ("me_dies10", md10), ("their_death10", th10), ("ours_first", first_ours), ("theirs_first", first_theirs)]
        bins(base, f"{name}: means by margin", cols)
        dec = base & (D["first"] > 0)
        print(f"  P(ours first | a death) by margin, {name}")
        m = D["m"]
        for a, b in zip(EDGES, EDGES[1:]):
            sel = dec & (m > a) & (m <= b) if a >= 0 else dec & (m > a) & (m <= min(b, -1e-9))
            if sel.sum() >= 50:
                print(f"    {a:+.2f}..{b:+.2f} n {int(sel.sum()):7}  {fmt(wmean(sel, first_ours))}")

if "jump" in sections or "all" in sections:
    for name, base in (("stand", stand), ("chase", chase)):
        for w in (0.1, 0.25, 0.5):
            print(f"\n# {name}: jump won - lost at m=0, bandwidth {w} (local linear; game bootstrap)")
            for t, y in (("bodies10", bodies10), ("bodies20", bodies20), ("me_dies10", md10), ("their_death10", th10), ("won_game", won)):
                print(f"   {t:14} {fmt(rdjump(base, y, w))}")

if "sub" in sections:
    hpf = D["hp"] / np.maximum(D["mhp"], 1)
    m = D["m"]
    subs = [("all", np.ones_like(stand)), ("hp>=0.9", hpf >= 0.9), ("hp 0.5-0.9", (hpf >= 0.5) & (hpf < 0.9)), ("hp<0.5", hpf < 0.5),
            ("1 ally (alone)", D["na"] == 1), ("2+ allies", D["na"] >= 2), ("1 enemy", D["ne"] == 1), ("2 enemies", D["ne"] == 2), ("3+ enemies", D["ne"] >= 3),
            ("unseen in roster", D["nunseen"] > 0), ("all seen", D["nunseen"] == 0), ("walkers", D["nwalk"] > 0), ("no walkers", D["nwalk"] == 0),
            ("gap<=2", (D["gap"] >= 0) & (D["gap"] <= 2)), ("gap 3-5", (D["gap"] >= 3) & (D["gap"] <= 5)), ("gap 6+", D["gap"] >= 6),
            ("ranged", D["ranged"] == 1), ("melee", D["ranged"] == 0), ("carrying 10+", D["gems"] >= 10),
            ("busy ally in roster", D["ally_busy"] > 0), ("falls (linked/lethal)", D["falls"] == 1)]
    for name, base in (("stand", stand), ("chase", chase)):
        print(f"\n## {name} by subgroup, |m|<=0.25: share of rows, P(ours first | death) won side / lost side, local-linear jump won-lost (bw .25) in bodies10 and won_game")
        for t, s in subs:
            b = base & s
            w_ = b & (m < 0) & (m >= -0.25) & (D["first"] > 0)
            l_ = b & (m > 0) & (m <= 0.25) & (D["first"] > 0)
            if w_.sum() < 100 or l_.sum() < 100:
                continue
            jb = rdjump(b, bodies10, 0.25)
            jw = rdjump(b, won, 0.25)
            print(f"  {t:24} n {int((b & (abs(m) <= 0.25)).sum()):7}  P1st won {100*wmean(w_, first_ours)[0]:5.1f}% / lost {100*wmean(l_, first_ours)[0]:5.1f}%   jump bodies {fmt(jb)}   won {fmt(jw)}")
