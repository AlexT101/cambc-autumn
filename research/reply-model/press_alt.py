"""Pressure trained on counterfactual alternatives (build_alt.py) vs on ordinary rollouts: ranking of held-out alternatives.

    python3 research/reply-model/press_alt.py MODEL.pkl ALT_TRAIN.npz... -- ALT_VAL.npz... [--out NEW.pkl]
"""
import pickle, sys
import numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import train  # noqa: E402

a = sys.argv[1:]
out = None
if "--out" in a:
    i = a.index("--out"); out = a[i + 1]; del a[i:i + 2]
k = a.index("--")
m = pickle.load(open(a[0], "rb"))
Pt = np.concatenate([np.load(p)["P"] for p in a[1:k]])
Pv = np.concatenate([np.load(p)["P"] for p in a[k + 1:]])
Dt = np.concatenate([np.load(p)["D"] for p in a[1:k]])
Dv = np.concatenate([np.load(p)["D"] for p in a[k + 1:]])
X, y = Pt[:, 5:-1], Pt[:, -1]
keep = X[:, 1] > 0
clf, reg = train.fit_pair(X[keep], y[keep], 60, 16, 10**7, 3)
m2 = dict(m); m2["press"] = (clf, reg)
Xv, yv = Pv[:, 5:-1], Pv[:, -1]
gv = Pv[:, 0].astype(np.int64) * 64 + Pv[:, 4].astype(np.int64)
for name, mm in (("rollout-trained", m), ("alt-trained", m2)):
    pm, pb, n = train.pairwise(gv, train.predict_press(mm, Xv), Xv[:, 1], yv)
    print(f"pressure {name}: pairs {n}, model right {pm:.3f}, strike-at-d {pb:.3f}")
# danger too
Xd, yd = Dt[:, 5:-1], Dt[:, -1]
keep = Xd[:, 1] > 0
dc, dr = train.fit_pair(Xd[keep], yd[keep], 60, 16, 10**7, 4)
m3 = dict(m); m3["danger"] = (dc, dr)
Xdv, ydv = Dv[:, 5:-1], Dv[:, -1]
g = Dv[:, 0].astype(np.int64) * 64 + Dv[:, 4].astype(np.int64)
for name, mm in (("rollout-trained", m), ("alt-trained", m3)):
    pm, pb, n = train.pairwise(g, train.predict_danger(mm, Xdv), train.HGR * Xdv[:, 1], ydv)
    print(f"danger {name}: pairs {n}, model right {pm:.3f}, ocean {pb:.3f}")
if out:
    pickle.dump(m2, open(out, "wb"))
