"""The recommended stand-in (PLAN2.md): compress.py's "r3 gam A+pairs cap" folded as the bot would evaluate it.

    python3 research/reply-model/fold.py [MODEL.pkl] [--bins 16,24,32]

Its hit logit is a sum of trees each on one feature or one listed pair. Every feature but d, blow and blow_stuns is
fixed for an enemy during a turn (my_hp for us), so the bot sums those terms once per enemy (z_e) and keeps, per
enemy, a table over d (0-6), one over blow bins and one over blow_stuns: a query is three lookups, a sigmoid table and
a multiply by min(blow, our health) x k. This script checks that folding is exact, then quantizes blow to B bins
(edges: quantiles of training blows) and scores each, as compress.py does; and runs lethal.py's P(killed) test with
the folded p in place of the full model's.
"""
import pickle
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import compress  # noqa: E402
import train  # noqa: E402

C = compress.C
N = train.DNAMES
# compress.py pickles its classes as __main__'s
for _k in ("Gam", "Coarse", "Table", "Flat"):
    setattr(sys.modules["__main__"], _k, getattr(compress, _k))


class Folded:
    """p from the model with blow replaced by its bin's training median (only inside the hit logit)."""

    def __init__(self, g, Xt, bins):
        self.g = g
        b = Xt[:, 1]
        self.edges = np.unique(np.quantile(b, np.linspace(0, 1, bins + 1)[1:-1]))
        k = np.searchsorted(self.edges, b, side="right")
        self.rep = np.array([np.median(b[k == i]) if (k == i).any() else 0 for i in range(len(self.edges) + 1)])

    def quant(self, X):
        Z = X.copy()
        Z[:, 1] = self.rep[np.searchsorted(self.edges, X[:, 1], side="right")]
        return Z

    def hit(self, X):
        return self.g.hit(self.quant(X))

    def danger(self, X):
        return self.g.mult(X) * self.hit(X) * self.g.k


def lethal(model_hit, va, cfg):
    X, y = va[:, 4:-1], va[:, -1]
    ph = model_hit(X)
    blow = X[:, 1]
    key = ((cfg.astype(np.int64) * (1 << 24) + va[:, 0].astype(np.int64)) * 4096 + va[:, 1].astype(np.int64)) * 64 + va[:, 2].astype(np.int64)
    u, inv = np.unique(key, return_inverse=True)
    n = np.bincount(inv)
    taken = np.bincount(inv, y)
    hp = np.zeros(len(u))
    hp[inv] = X[:, 12]
    worst = np.bincount(inv, blow)
    killed = taken >= hp - 0.5
    order = np.argsort(inv, kind="stable")
    starts = np.r_[0, np.cumsum(n)]
    pkb = np.zeros(len(u))
    for g in np.nonzero(worst >= hp)[0]:
        rows = order[starts[g]:starts[g + 1]]
        if len(rows) > 6:
            rows = rows[np.argsort(-blow[rows])[:6]]
        p, b = ph[rows], blow[rows]
        tot = 0.0
        for mask in range(1, 1 << len(rows)):
            bits = np.array([(mask >> i) & 1 for i in range(len(rows))], bool)
            if b[bits].sum() >= hp[g]:
                tot += np.prod(np.where(bits, p, 1 - p))
        pkb[g] = tot
    print(f"  Pblow(killed) log loss {train.logloss(pkb, killed.astype(float)):.4f} "
          f"(constant {train.logloss(np.full(len(u), killed.mean()), killed.astype(float)):.4f})")
    for name, flag in (("worst >= health", worst >= hp), *((f"Pblow(killed) >= {t:.2f}", pkb >= t) for t in (0.05, 0.1, 0.2, 0.35, 0.5))):
        tp = (flag & killed).sum()
        print(f"  lethal {name:22s} flags {flag.mean():.4f}  recall {tp / max(1, killed.sum()):.3f}  precision {tp / max(1, flag.sum()):.3f}")


def main():
    a = sys.argv[1:]
    bins = [16, 24, 32]
    if "--bins" in a:
        i = a.index("--bins")
        bins = [int(v) for v in a[i + 1].split(",")]
        del a[i:i + 2]
    path = a[0] if a else f"{C}/r3_gam_Appairs_cap.pkl"
    g = pickle.load(open(path, "rb"))
    t = np.load(f"{C}/train.npy")
    va = np.load(f"{C}/val.npy")
    Xv, yv, cv = va[:, 4:-1], va[:, -1], np.load(f"{C}/val_cfg.npy")
    alt = np.load(f"{C}/alt.npy")
    # Which features its trees read, and that every tree's features are one of: per-tile ones alone, or fixed ones.
    tabs = g.tables()
    tile = {"d", "blow", "blow_stuns"}
    mixed = [k for k in tabs if len(set(k) & tile) > 1]
    print(f"{path}: {len(g.names)} features, {len(tabs)} tables; trees on two per-tile features: {mixed or 'none'}")
    print("  per-tile tables after folding:", sorted({tuple(sorted(set(k) & tile)) for k in tabs if set(k) & tile}))
    compress.score("unquantized", g, Xv, yv, cv, alt)
    for b in bins:
        compress.score(f"blow in {b} bins", Folded(g, t[:400_000, 4:-1], b), Xv, yv, cv, alt)
    print("lethal, folded p (blow exact):")
    lethal(g.hit, va, cv)
    print("lethal, full model p:")
    m = pickle.load(open("replays/combatlab/reply/m1.pkl", "rb"))
    lethal(lambda X: m["danger"][0].predict_proba(X)[:, 1], va, cv)


if __name__ == "__main__":
    main()
