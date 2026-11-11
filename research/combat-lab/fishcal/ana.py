"""Tables for fishcal rows (collect.py), split by source: self-play, Fish, Mite. 95% CIs by a Poisson bootstrap over games.

    python3 ana.py ROWS.jsonl.gz [...] [--sections calib,jump,members,damage,hg,sub] [--max-round R]

Each input's .hg.jsonl.gz twin holds its HG rows."""
import argparse, gzip, json
from collections import defaultdict
import numpy as np

LEAVE = set("RK")
EDGES = [-99, -3, -1.5, -1, -0.5, -0.25, -0.1, 0, 0.1, 0.25, 0.5, 1, 1.5, 3, 99]
B = 200
rng = np.random.default_rng(1)


def src_of(d):
    return {"Intercontinental Fish": "fish", "Mite": "mite"}.get(d["opp"], "self")


class Table:
    """Columns as arrays plus a game index for clustered bootstrap."""

    def __init__(self, rows, cols):
        games = {}
        self.g = np.array([games.setdefault((d["version"], d["game"]), len(games)) for d in rows], dtype=np.int64)
        self.ng = max(len(games), 1)
        self.W = rng.poisson(1.0, size=(B, self.ng)).astype(float)
        self.c = {k: np.array([f(d) for d in rows], dtype=float) for k, f in cols.items()}
        self.n = len(rows)

    def mean(self, mask, y):
        s = np.bincount(self.g[mask], weights=y[mask], minlength=self.ng)
        n = np.bincount(self.g[mask], minlength=self.ng).astype(float)
        bs = (self.W @ s) / np.maximum(self.W @ n, 1e-9)
        return s.sum() / max(n.sum(), 1e-9), np.percentile(bs, 2.5), np.percentile(bs, 97.5), int(n.sum())

    def ratio(self, mask, num, den):
        s = np.bincount(self.g[mask], weights=num[mask], minlength=self.ng)
        n = np.bincount(self.g[mask], weights=den[mask], minlength=self.ng)
        bs = (self.W @ s) / np.maximum(self.W @ n, 1e-9)
        return s.sum() / max(n.sum(), 1e-9), np.percentile(bs, 2.5), np.percentile(bs, 97.5), int(mask.sum())

    def jump(self, base, y, w):
        m = self.c["m"]

        def inter(mask, wg):
            x, yy, ww = m[mask], y[mask], wg[self.g[mask]]
            sw = ww.sum()
            mx, my = (ww * x).sum() / sw, (ww * yy).sum() / sw
            b = (ww * (x - mx) * (yy - my)).sum() / max((ww * (x - mx) ** 2).sum(), 1e-12)
            return my - b * mx
        won, lost = base & (m < 0) & (m >= -w), base & (m > 0) & (m <= w)
        if won.sum() < 30 or lost.sum() < 30:
            return float("nan"), float("nan"), float("nan"), int(won.sum()), int(lost.sum())
        est = inter(won, np.ones(self.ng)) - inter(lost, np.ones(self.ng))
        bs = [inter(won, self.W[i]) - inter(lost, self.W[i]) for i in range(100)]
        return est, np.percentile(bs, 2.5), np.percentile(bs, 97.5), int(won.sum()), int(lost.sum())


def fmt(t, pct=False):
    k = 100 if pct else 1
    return f"{k * t[0]:+.3f} ({k * t[1]:+.3f}..{k * t[2]:+.3f})" if not pct else f"{k * t[0]:5.1f}% ({k * t[1]:.1f}-{k * t[2]:.1f})"


def load(paths, max_round):
    """Rows of every input; a live game played identically more than once (the same ladder replay, in one version or
    several) counts once, under the first game that holds it."""
    rows, hrows, owner = [], [], {}

    def keep(d, p):
        k = d.get("rsha")
        return d["r"] <= max_round and (k is None or owner.setdefault(k, (p, d["game"])) == (p, d["game"]))
    for p in paths:
        rows += [d for d in map(json.loads, gzip.open(p, "rt")) if keep(d, p)]
        hp = p.replace(".jsonl.gz", ".hg.jsonl.gz")
        try:
            hrows += [d for d in map(json.loads, gzip.open(hp, "rt")) if keep(d, p)]
        except FileNotFoundError:
            pass
    return rows, hrows


def bin_masks(m):
    for a, b in zip(EDGES, EDGES[1:]):
        if b <= 0:
            yield f"{a:+.2f}..{b:+.2f}", (m > a) & (m <= b) & (m < 0) if b == 0 else (m > a) & (m <= b)
        else:
            yield f"{a:+.2f}..{b:+.2f}", (m > a) & (m <= b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", nargs="+")
    ap.add_argument("--sections", default="calib,jump,members,damage,hg")
    ap.add_argument("--max-round", type=int, default=10**9)
    ap.add_argument("--full-games", action="store_true", help="live games only where the re-run reproduced the whole ladder game")
    a = ap.parse_args()
    sec = set(a.sections.split(","))
    rows, hrows = load(a.rows, a.max_round)
    if a.full_games:
        full = lambda d: d.get("trusted") is None or d["trusted"] >= d["rounds"]
        rows, hrows = [d for d in rows if full(d)], [d for d in hrows if full(d)]
    by = defaultdict(list)
    for d in rows:
        by[src_of(d)].append(d)
    srcs = [s for s in ("self", "fish", "mite") if by[s]]
    T = {}
    for s in srcs:
        T[s] = Table(by[s], {
            "m": lambda d: d["m"], "stand": lambda d: d["tag"] == "CS", "chase": lambda d: d["tag"] == "CC",
            "bodies10": lambda d: d["theirs_dead10"] - d["ours_dead10"], "bodies20": lambda d: d["theirs_dead20"] - d["ours_dead20"],
            "md10": lambda d: d["me_dies10"], "th10": lambda d: d["theirs_dead10"] > 0, "won": lambda d: d["won_game"],
            "death": lambda d: d["first"] != "none", "ours_first": lambda d: d["first"] == "ours",
            "leave": lambda d: d["dec"] in LEAVE, "t5": lambda d: d["sim_t5"], "o5": lambda d: d["sim_o5"],
            "t1": lambda d: d["sim_t1"], "o1": lambda d: d["sim_o1"], "theirs5": lambda d: d["theirs5"], "ours5": lambda d: d["ours5"],
            "v1ok": lambda d: d["v1"] == d["verdict"], "hpf": lambda d: d["hp"] / max(d["mhp"], 1),
            "nunseen": lambda d: sum(1 for e in d["enemies"] if not e["vis"]), "ne": lambda d: len(d["enemies"]),
            "na": lambda d: len(d["allies"]),
        })
        t = T[s]
        print(f"{s}: {t.n} verdict rows ({int(t.c['stand'].sum())} stand, {int(t.c['chase'].sum())} chase) in {t.ng} games; "
              f"recomputed verdict = live verdict on {100 * t.c['v1ok'].mean():.2f}%")

    if "calib" in sec:
        for kind in ("stand", "chase"):
            print(f"\n## {kind}: P(our side loses a champion first | a death within 10 rounds), by margin")
            print(f"{'margin':14} " + " ".join(f"{s:>30}" for s in srcs))
            for name, _ in bin_masks(np.zeros(1)):
                cells = []
                for s in srcs:
                    t = T[s]
                    mk = dict(bin_masks(t.c["m"]))[name] & (t.c[kind] > 0) & (t.c["death"] > 0)
                    cells.append(f"{fmt(t.mean(mk, t.c['ours_first']), True):>22} n{int(mk.sum()):>7}" if mk.sum() >= 30 else f"{'':>30}")
                print(f"{name:14} " + " ".join(cells))
            print(f"\n## {kind}: bodies/10 rounds (their dead - ours, by pick) and our champion's death within 10, by margin")
            for name, _ in bin_masks(np.zeros(1)):
                cells = []
                for s in srcs:
                    t = T[s]
                    mk = dict(bin_masks(t.c["m"]))[name] & (t.c[kind] > 0)
                    cells.append(f"{t.mean(mk, t.c['bodies10'])[0]:+.3f} {100 * t.mean(mk, t.c['md10'])[0]:5.1f}% n{int(mk.sum()):>7}" if mk.sum() >= 30 else f"{'':>26}")
                print(f"{name:14} " + " ".join(f"{c:>30}" for c in cells))

    if "jump" in sec:
        for kind in ("stand", "chase"):
            for w in (0.25, 0.5):
                print(f"\n## {kind}: jump won - lost at m = 0, bandwidth {w} (local linear)")
                for s in srcs:
                    t = T[s]
                    base = t.c[kind] > 0
                    out = [f"{y}: {fmt(t.jump(base, t.c[y], w))}" for y in ("bodies10", "bodies20", "md10", "th10", "won")]
                    print(f"  {s:5} n {t.jump(base, t.c['m'], w)[3:]}  " + "  ".join(out))
                    pw = base & (t.c["death"] > 0)
                    print(f"        P(ours first | death): won side {fmt(t.mean(pw & (t.c['m'] < 0) & (t.c['m'] >= -w), t.c['ours_first']), True)}, "
                          f"lost side {fmt(t.mean(pw & (t.c['m'] > 0) & (t.c['m'] <= w), t.c['ours_first']), True)}")

    if "sub" in sec:
        for kind in ("stand", "chase"):
            print(f"\n## {kind} subgroups at the boundary: P(ours first | death) won / lost side (|m| <= 0.25), jump won - lost (bw 0.25) in bodies10 and games won")
            for s in srcs:
                t = T[s]
                c, m = t.c, t.c["m"]
                subs = [("all", m == m), ("health >= 90%", c["hpf"] >= 0.9), ("health < 50%", c["hpf"] < 0.5), ("alone", c["na"] <= 1),
                        ("2+ allies", c["na"] >= 3), ("3+ enemies", c["ne"] >= 3), ("unseen enemy", c["nunseen"] > 0), ("all seen", c["nunseen"] == 0)]
                for name, sm in subs:
                    b = (c[kind] > 0) & sm
                    w_ = b & (m < 0) & (m >= -0.25) & (c["death"] > 0)
                    l_ = b & (m > 0) & (m <= 0.25) & (c["death"] > 0)
                    if w_.sum() < 60 or l_.sum() < 60:
                        continue
                    print(f"  {s:5} {name:16} P1st {100 * t.mean(w_, c['ours_first'])[0]:5.1f}% / {100 * t.mean(l_, c['ours_first'])[0]:5.1f}%  "
                          f"bodies {fmt(t.jump(b, c['bodies10'], 0.25))}  won {fmt(t.jump(b, c['won'], 0.25))}")

    if "members" in sec:
        print("\n## stand roster members that hit within arrival + 1 rounds, our champion staying (decision not R/K)")
        acc = {s: defaultdict(list) for s in srcs}
        for s in srcs:
            for d in by[s]:
                if d["tag"] != "CS" or d["dec"] in LEAVE:
                    continue
                for e in d["enemies"]:
                    acc[s][("enemy", "seen" if e["vis"] else "unseen", min(e["arr"], 3))].append(e["hit"] <= min(e["arr"], 3) + 1)
                for x in d["allies"]:
                    if x["id"] != d["me"]:
                        acc[s][("ally", "", min(x["arr"], 3))].append(x["hit"] <= min(x["arr"], 3) + 1)
        keys = sorted(set().union(*[acc[s].keys() for s in srcs]))
        print(f"{'member':28} " + " ".join(f"{s:>20}" for s in srcs))
        for k in keys:
            print(f"{str(k):28} " + " ".join(f"{100 * np.mean(acc[s][k]):6.1f}% n{len(acc[s][k]):>9}" if acc[s][k] else f"{'':>20}" for s in srcs))

    if "damage" in sec:
        print("\n## realized / simulated damage over 5 rounds, stand rows where our champion stays and both sides strike in the sim's first turn")
        for s in srcs:
            t = T[s]
            for lab, band in (("all", np.abs(t.c["m"]) <= 99), ("|m|<=0.5", np.abs(t.c["m"]) <= 0.5)):
                mk = (t.c["stand"] > 0) & (t.c["leave"] == 0) & (t.c["t1"] > 0) & (t.c["o1"] > 0) & band
                th = t.ratio(mk, t.c["theirs5"], t.c["t5"])
                ou = t.ratio(mk, t.c["ours5"], t.c["o5"])
                # Balance: (theirs realized / sim) over (ours realized / sim); > 1 means they deliver more of theirs than we do of ours.
                bal = (th[0] / ou[0]) if ou[0] > 0 else float("nan")
                print(f"  {s:5} {lab:9} n {th[3]:7}  theirs {fmt(th)}  ours {fmt(ou)}  balance {bal:.3f}")

    if "hg" in sec and hrows:
        hb = defaultdict(list)
        for d in hrows:
            hb[src_of(d)].append(d)
        hs = [s for s in ("self", "fish", "mite") if hb[s]]
        H = {s: Table(hb[s], {"real": lambda d: d["real"], "blow": lambda d: d["blow"], "at": lambda d: d["at"], "hit": lambda d: d["real"] > 0,
                               "d": lambda d: d["d"], "pos": lambda d: d["pos_ok"], "fight": lambda d: d["dec"] in "CAG",
                               "priced": lambda d: d.get("priced", 0)}) for s in hs}
        print("\n## hit_given_reach: the share of a reaching enemy's priced damage it then delivers before our next turn (params: 0.234)")
        print("   real/blow = sum of realized damage over sum of blow(e, p); P(hit) = share of reaching enemies that damage us at all")
        for lab, sel in (("all turns", lambda h: np.ones(h.n, bool)), ("end tile priced by the strike search", lambda h: h.c["priced"] > 0),
                         ("fight turns (C/A/G)", lambda h: h.c["fight"] > 0), ("other turns", lambda h: (h.c["fight"] == 0) & (h.c["priced"] == 0))):
            print(f"  {lab}")
            for s in hs:
                h = H[s]
                mk = sel(h) & (h.c["blow"] > 0)
                print(f"    {s:5} n {int(mk.sum()):8}  real/blow {fmt(h.ratio(mk, h.c['real'], h.c['blow']))}  real/at {fmt(h.ratio(mk, h.c['real'], h.c['at']))}  "
                      f"P(hit) {fmt(h.mean(mk, h.c['hit']), True)}  position matches replay {100 * h.c['pos'][mk].mean():.1f}%")
        print("  by distance (priced end tiles)")
        for dd in range(0, 7):
            cells = []
            for s in hs:
                h = H[s]
                mk = (h.c["priced"] > 0) & (h.c["blow"] > 0) & (h.c["d"] == dd)
                cells.append(f"{fmt(h.ratio(mk, h.c['real'], h.c['blow'])):>26} n{int(mk.sum()):>7}" if mk.sum() >= 30 else f"{'':>34}")
            print(f"    d={dd} " + " ".join(cells))
        print("  by enemy type (priced end tiles, real/blow)")
        types = sorted({d["etype"] for d in hrows})
        for ty in types:
            cells = []
            for s in hs:
                h = H[s]
                mk = (h.c["priced"] > 0) & (h.c["blow"] > 0) & np.array([d["etype"] == ty for d in hb[s]])
                cells.append(f"{fmt(h.ratio(mk, h.c['real'], h.c['blow'])):>26} n{int(mk.sum()):>7}" if mk.sum() >= 30 else f"{'':>34}")
            print(f"    {ty:14} " + " ".join(cells))


if __name__ == "__main__":
    main()
