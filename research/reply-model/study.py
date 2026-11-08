"""Cost against accuracy: single expected-damage regressors of several sizes, and feature importance.

    python3 research/reply-model/study.py TRAIN.npz [...] -- VAL.npz [...]

Cost is the mean number of splits a row passes (summed over trees), on the held-out rows: about 4 WASM
instructions each in the exported if-else code.
"""
import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import train  # noqa: E402


def path_len(est, X):
    total = np.zeros(len(X))
    for p in est._predictors:
        nodes = p[0].nodes
        i = np.zeros(len(X), dtype=np.int64)
        depth = np.zeros(len(X))
        active = nodes["is_leaf"][i] == 0
        while active.any():
            nd = nodes[i[active]]
            go_left = X[active, nd["feature_idx"]] <= nd["num_threshold"]
            i[active] = np.where(go_left, nd["left"], nd["right"])
            depth[active] += 1
            active = nodes["is_leaf"][i] == 0
        total += depth
    return total.mean()


def r2(pred, y):
    return 1 - np.mean((pred - y) ** 2) / np.var(y)


def main():
    a = sys.argv[1:]
    k = a.index("--")
    D, P, Dc, Pc = train.load(a[:k])
    Dv, Pv, Dcv, Pcv = train.load(a[k + 1:])
    for name, rows in (("danger", train.danger_rows), ("press", train.press_rows)):
        X, y, _, _ = rows(D if name == "danger" else P, Dc if name == "danger" else Pc)
        Xv, yv, _, _ = rows(Dv if name == "danger" else Pv, Dcv if name == "danger" else Pcv)
        rng = np.random.default_rng(0)
        i = rng.choice(len(y), min(len(y), 600_000), replace=False)
        X, y = X[i], y[i]
        Xv, yv = Xv[:200_000], yv[:200_000]
        base = (X[:, 1] * y).sum() / (X[:, 1] ** 2).sum()
        print(f"{name}: refit-multiple R2 {r2(base * Xv[:, 1], yv):.3f}")
        best = None
        for trees, leaves in ((15, 16), (30, 16), (20, 32), (40, 32), (60, 32)):
            m = HistGradientBoostingRegressor(max_iter=trees, max_leaf_nodes=leaves, learning_rate=0.15 if trees <= 30 else 0.1,
                                              min_samples_leaf=200, l2_regularization=1.0, early_stopping=False, random_state=0)
            m.fit(X, y)
            pv = m.predict(Xv)
            print(f"  {trees:3d} trees x {leaves:2d} leaves: R2 {r2(pv, yv):.3f} cost {path_len(m, Xv[:20000]):.0f} splits")
            if (trees, leaves) == (40, 32):
                best = m
        # permutation importance on the 40x32 model
        pv = best.predict(Xv[:50000])
        base_mse = np.mean((pv - yv[:50000]) ** 2)
        imp = []
        names = train.DNAMES if name == "danger" else train.PNAMES
        for f in range(X.shape[1]):
            Xp = Xv[:50000].copy()
            Xp[:, f] = rng.permutation(Xp[:, f])
            imp.append((np.mean((best.predict(Xp) - yv[:50000]) ** 2) / base_mse - 1, names[f]))
        imp.sort(reverse=True)
        print("  importance (MSE rise when permuted): " + ", ".join(f"{n} {v:.3f}" for v, n in imp))


if __name__ == "__main__":
    main()
