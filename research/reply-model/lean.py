"""A lean danger term: one boosted regressor of e's next-turn damage on a cheap subset of danger_features.

    python3 research/reply-model/lean.py fit TRAIN.npz [...] -- VAL.npz [...] -- ALTVAL.npz [...] --out M.pkl
        [--features a,b,c] [--trees N] [--leaves L] [--rows R]
    python3 research/reply-model/lean.py export M.pkl HEADER.h

Rows with a blow > 0, as train.py's. The regressor is fitted on the subset; the export indexes the full
danger_features layout, so the bot fills only the subset's slots.
"""
import pickle
import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import train  # noqa: E402
from study import path_len, r2  # noqa: E402

DEFAULT = ["d", "blow", "blow_stuns", "n_src", "n_src_basic", "n_src_safe", "src_here", "e_ttd", "mate_hp_near", "foe_hp_near",
           "p_bush", "e_turns", "my_hp", "e_channel", "e_hp_frac", "e_dash_ready", "e_hp", "e_str", "e_type", "alt_min_hp_frac",
           "alt_best", "my_hp_frac", "n_alt", "e_cd1", "e_hurt", "my_type", "e_gems", "e_ranged"]


PRESS = [n for n in train.PNAMES if n != "t_blow_on_me"]


def alt_rows(paths, key):
    A = np.concatenate([np.load(p)[key] for p in paths])
    X = A[:, 5:-1]
    keep = X[:, 1] > 0
    return X[keep], A[keep, -1]


def fit(a, opt):
    if opt.get("--term") == "press":
        return fit_press(a, opt)
    i, j = a.index("--"), len(a) - 1 - a[::-1].index("--")
    names = opt.get("--features", ",".join(DEFAULT)).split(",")
    idx = [train.DNAMES.index(n) for n in names]
    D, _, Dc, _ = train.load(a[:i])
    X, y, _, _ = train.danger_rows(D, Dc)
    rows = int(opt.get("--rows", 1_500_000))
    rng = np.random.default_rng(0)
    if len(y) > rows:
        k = rng.choice(len(y), rows, replace=False)
        X, y = X[k], y[k]
    trees, leaves = int(opt.get("--trees", 30)), int(opt.get("--leaves", 16))
    m = HistGradientBoostingRegressor(max_iter=trees, max_leaf_nodes=leaves, learning_rate=0.15 if trees <= 30 else 0.1,
                                      min_samples_leaf=200, l2_regularization=1.0, early_stopping=False, random_state=0)
    m.fit(X[:, idx], y)
    Dv, _, Dcv, _ = train.load(a[i + 1:j])
    Xv, yv, _, _ = train.danger_rows(Dv, Dcv)
    pv = np.maximum(m.predict(Xv[:, idx]), 0)
    print(f"{len(names)} features, {trees}x{leaves}: R2 {r2(pv, yv):.3f} (ocean {r2(train.HGR * Xv[:, 1], yv):.3f}),"
          f" corr {np.corrcoef(pv, yv)[0, 1]:.3f}, mean {pv.mean():.1f} vs {yv.mean():.1f},"
          f" cost {path_len(m, Xv[:20000, idx]):.0f} splits")
    A = np.concatenate([np.load(p)["D"] for p in a[j + 1:]])
    Xa, ya = A[:, 5:-1], A[:, -1]
    g = A[:, 0].astype(np.int64) * 64 + A[:, 4].astype(np.int64)
    pa = np.where(Xa[:, 1] > 0, np.maximum(m.predict(Xa[:, idx]), 0), 0)
    pm, pb, n = train.pairwise(g, pa, train.HGR * Xa[:, 1], ya)
    print(f"  alternatives: {n} pairs, lean right {pm:.3f}, ocean {pb:.3f}")
    pickle.dump({"est": m, "idx": idx, "names": names}, open(opt["--out"], "wb"))


def fit_press(a, opt):
    """Pressure from the counterfactual rows (build_alt.py) alone: TRAIN_ALT... -- VAL_ALT..."""
    i = a.index("--")
    names = opt.get("--features", ",".join(PRESS)).split(",")
    idx = [train.PNAMES.index(n) for n in names]
    X, y = alt_rows(a[:i], "P")
    trees, leaves = int(opt.get("--trees", 12)), int(opt.get("--leaves", 32))
    m = HistGradientBoostingRegressor(max_iter=trees, max_leaf_nodes=leaves, learning_rate=0.15 if trees <= 30 else 0.1,
                                      min_samples_leaf=200, l2_regularization=1.0, early_stopping=False, random_state=0)
    m.fit(X[:, idx], y)
    A = np.concatenate([np.load(p)["P"] for p in a[i + 1:]])
    Xa, ya = A[:, 5:-1], A[:, -1]
    k = Xa[:, 1] > 0
    pa = np.where(k, np.maximum(m.predict(Xa[:, idx]), 0), 0)
    refit = (Xa[k, 1] * ya[k]).sum() / (Xa[k, 1] ** 2).sum()
    print(f"press {len(names)} features, {trees}x{leaves}, {len(y)} rows: R2 {r2(pa[k], ya[k]):.3f} "
          f"(strike multiple {r2(refit * Xa[k, 1], ya[k]):.3f}), cost {path_len(m, Xa[k][:20000][:, idx]):.0f} splits")
    g = A[:, 0].astype(np.int64) * 64 + A[:, 4].astype(np.int64)
    pm, pb, n = train.pairwise(g, pa, Xa[:, 1], ya)
    print(f"  alternatives: {n} pairs, lean right {pm:.3f}, strike-at-d {pb:.3f}")
    pickle.dump({"est": m, "idx": idx, "names": names, "term": "press"}, open(opt["--out"], "wb"))


def export(path, header):
    m = pickle.load(open(path, "rb"))
    est, idx = m["est"], m["idx"]
    press = m.get("term") == "press"
    names_all, pre, fn = (train.PNAMES, "press", "pressure") if press else (train.DNAMES, "lean", "danger")
    trees = []
    for t, p in enumerate(est._predictors):
        code = train.tree_code(p[0], [names_all[f] for f in idx], f"{pre}_t{t}")
        for f in sorted(range(len(idx)), reverse=True):  # remap subset columns to the full layout
            code = code.replace(f"x[{f}] <=", f"x[@{idx[f]}] <=")
        trees.append(code.replace("x[@", "x["))
    base = float(np.ravel(est._baseline_prediction)[0])
    body = " + ".join(f"{pre}_t{t}(x)" for t in range(len(trees)))
    used = ", ".join(str(i) for i in sorted(idx))
    ns = "press_lean" if press else "lean"
    parts = ["// Generated by research/reply-model/lean.py export: do not edit.", "#pragma once", "#include <algorithm>", "",
             f"namespace aph::reply::{ns} {{", "namespace detail {", *trees, "} // namespace detail",
             f"// {'pressure' if press else 'danger'}_features slots it reads: {used}.",
             f"inline float {fn}(const float* x) {{ using namespace detail; return std::max(0.0f, {train.lit(base)} + {body}); }}",
             f"}} // namespace aph::reply::{ns}\n"]
    open(header, "w").write("\n".join(parts))
    print(f"{header}: {len(trees)} trees, slots {used}")


def main():
    a = sys.argv[1:]
    opt = {}
    for k in ("--out", "--trees", "--leaves", "--rows", "--features", "--term"):
        if k in a:
            i = a.index(k)
            opt[k] = a[i + 1]
            del a[i:i + 2]
    if a[0] == "fit":
        fit(a[1:], opt)
    else:
        export(a[1], a[2])


if __name__ == "__main__":
    main()
