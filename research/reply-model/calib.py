"""Mean calibration of the danger modes (PLAN2.md section 3.3.3): each mode's multiplier so that its mean expected
damage on the training rows (blow > 0) equals the true mean, and the unseen rate in the same units.

    python3 research/reply-model/calib.py
"""
import pickle
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import compress  # noqa: E402
import train  # noqa: E402

for _k in ("Gam", "Coarse", "Table", "Flat"):
    setattr(sys.modules["__main__"], _k, getattr(compress, _k))
C = compress.C
t = np.load(f"{C}/train.npy", mmap_mode="r")[:600_000]
X, y = np.asarray(t[:, 4:-1], dtype=np.float64), np.asarray(t[:, -1], dtype=np.float64)
va = np.load(f"{C}/val.npy")
Xv, yv = va[:, 4:-1].astype(np.float64), va[:, -1].astype(np.float64)
cap = lambda Z: np.minimum(Z[:, 1], np.maximum(Z[:, 12], 1))
for name in ("r3_gam_Appairs_cap", "r5_gam_min5_cap"):
    g = pickle.load(open(f"{C}/{name}.pkl", "rb"))
    d = g.danger(X)
    r = y.sum() / d.sum()
    dv = g.danger(Xv) * r
    print(f"{name}: k {g.k:.5f} rescale {r:.5f} (k x rescale {g.k * r:.5f}); val mean {dv.mean():.2f} / {yv.mean():.2f}")
pbar = y.sum() / cap(X).sum()
print(f"flat: p x k over min(blow, hp) {pbar:.5f}; val mean {(pbar * cap(Xv)).mean():.2f}")
u = y.sum() / X[:, 1].sum()
print(f"unseen (blow, uncapped): {u:.5f}; hit_given_reach {train.HGR}; ratio {u / train.HGR:.4f}")
print(f"flat 0.234 x blow val mean {(train.HGR * Xv[:, 1]).mean():.2f}; true {yv.mean():.2f}; c = {(train.HGR * Xv[:, 1]).mean() / yv.mean():.4f}")
