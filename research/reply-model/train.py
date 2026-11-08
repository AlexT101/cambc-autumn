"""Fit the reply model's danger and pressure terms and compare them with ocean's flat danger.

    python3 research/reply-model/train.py fit TRAIN.npz [...] --out MODEL.pkl [--trees N --leaves L --rows R]
    python3 research/reply-model/train.py eval MODEL.pkl VAL.npz [...]
    python3 research/reply-model/train.py export MODEL.pkl HEADER.h

Danger (rows with a Reach blow > 0, the only ones the bot prices): P(hit) by a boosted classifier and the damage
given a hit by a boosted regressor; expected damage = their product. Pressure: the same for our next-turn hit on
the target. Baselines: ocean's 0.234 x blow (hit 0.234 where blow > 0), the same refitted on the training rows
(a constant hit rate and a least-squares multiple of the blow), and for pressure the refitted constant hit rate
where our strike reaches and a multiple of our strike's damage.
"""
import pickle
import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

DNAMES = ["d", "blow", "blow_stuns", "strike_at", "e_type", "e_ranged", "e_hp", "e_hp_frac", "e_str", "e_dash_ready", "e_cd0",
          "e_cd1", "my_hp", "my_hp_frac", "my_type", "my_ranged", "my_gems", "n_src", "n_src_basic", "n_src_safe", "n_src_nocamp",
          "n_src_free", "src_here", "e_in_zone", "our_dmg_on_e", "e_ttd", "n_alt", "alt_min_hp_frac", "alt_best", "alt_gems",
          "foes_near", "mates_near", "foe_hp_near", "mate_hp_near", "p_bush", "e_bush", "p_open", "e_gems", "e_spawn_steps",
          "e_channel", "e_turns", "camp_p", "moved", "my_strike_on_e", "e_stun_pending", "e_hurt", "n_vis", "n_mates"]
PNAMES = ["d", "my_strike_at", "my_reach", "t_type", "t_ranged", "t_hp", "t_hp_frac", "t_gems", "t_dash_ready", "t_cd0", "t_cd1",
          "t_moves", "t_out_me", "t_out_basic", "t_out_team", "t_blow_on_me", "ally_dmg_on_t", "t_ttd", "my_hp_frac", "my_type",
          "my_ranged", "my_hp", "foes_near_t", "mates_near_t", "t_bush", "p_bush", "t_channel", "t_spawn_steps", "t_open", "moved",
          "t_stun_pending", "t_turns", "t_camp", "t_hurt", "my_basic_reach", "t_out_free"]
assert len(DNAMES) == 48 and len(PNAMES) == 36
CFG = ["oo", "oa", "ao"]
HGR = 0.2338928


def load(paths):
    D, P, Dc, Pc = [], [], [], []
    for p in paths:
        z = np.load(p)
        D.append(z["D"]), P.append(z["P"]), Dc.append(z["Dc"]), Pc.append(z["Pc"])
    return np.concatenate(D), np.concatenate(P), np.concatenate(Dc), np.concatenate(Pc)


def danger_rows(D, Dc):
    X = D[:, 4:-1]
    keep = X[:, 1] > 0
    return X[keep], D[keep, -1], Dc[keep], D[keep, 0]


def press_rows(P, Pc):
    X = P[:, 4:-1]
    keep = X[:, 1] > 0  # our strike reaches the target's tile next turn if it stays
    return X[keep], P[keep, -1], Pc[keep], P[keep, 0]


def fit_pair(X, y, trees, leaves, rows, seed):
    rng = np.random.default_rng(seed)
    if len(y) > rows:
        i = rng.choice(len(y), rows, replace=False)
        X, y = X[i], y[i]
    hit = y > 0.5
    cat = None
    clf = HistGradientBoostingClassifier(max_iter=trees, max_leaf_nodes=leaves, learning_rate=0.1, min_samples_leaf=200,
                                         l2_regularization=1.0, early_stopping=False, random_state=seed)
    clf.fit(X, hit)
    reg = HistGradientBoostingRegressor(max_iter=trees, max_leaf_nodes=leaves, learning_rate=0.1, min_samples_leaf=200,
                                        l2_regularization=1.0, early_stopping=False, random_state=seed)
    reg.fit(X[hit], y[hit])
    return clf, reg


def logloss(p, y):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def calib(p, y, bins=(0, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.01)):
    out = []
    for a, b in zip(bins[:-1], bins[1:]):
        m = (p >= a) & (p < b)
        if m.sum() >= 50:
            out.append(f"[{a:.2f},{b:.2f}) n={m.sum()} pred {p[m].mean():.3f} obs {y[m].mean():.3f}")
    return out


def fit(paths, out, trees=60, leaves=16, rows=1_500_000):
    D, P, Dc, Pc = load(paths)
    Xd, yd, _, _ = danger_rows(D, Dc)
    Xp, yp, _, _ = press_rows(P, Pc)
    print(f"danger rows {len(yd)}, pressure rows {len(yp)}")
    m = {"trees": trees, "leaves": leaves}
    m["danger"] = fit_pair(Xd, yd, trees, leaves, rows, 1)
    m["press"] = fit_pair(Xp, yp, trees, leaves, rows, 2)
    # Refitted baselines.
    m["base_d"] = (float((yd > 0.5).mean()), float((Xd[:, 1] * yd).sum() / (Xd[:, 1] ** 2).sum()))
    m["base_p"] = (float((yp > 0.5).mean()), float((Xp[:, 1] * yp).sum() / (Xp[:, 1] ** 2).sum()))
    print("refit baselines: danger hit %.3f, x blow %.3f; pressure hit %.3f, x strike %.3f" % (m["base_d"] + m["base_p"]))
    with open(out, "wb") as f:
        pickle.dump(m, f)


def report(name, X, y, c, clf, reg, base_hit, base_mult, ref, ref_hit):
    hit = (y > 0.5).astype(float)
    ph = clf.predict_proba(X)[:, 1]
    pm = reg.predict(X)
    ed = ph * np.maximum(pm, 0)
    for k in range(3):
        mk = c == k
        if mk.sum() < 100:
            continue
        yk, hk = y[mk], hit[mk]
        line = [f"{name} {CFG[k]} n={mk.sum()} hit-rate {hk.mean():.3f} mean {yk.mean():.1f}"]
        if ref_hit is not None:
            line.append(f"logloss model {logloss(ph[mk], hk):.4f} ocean {logloss(np.full(mk.sum(), ref_hit), hk):.4f} "
                        f"refit {logloss(np.full(mk.sum(), base_hit), hk):.4f}")
        else:
            line.append(f"logloss model {logloss(ph[mk], hk):.4f} refit {logloss(np.full(mk.sum(), base_hit), hk):.4f}")
        mse_m = np.mean((ed[mk] - yk) ** 2)
        mse_r = np.mean((base_mult * ref[mk] - yk) ** 2)
        var = np.var(yk)
        if ref_hit is not None:
            mse_o = np.mean((HGR * ref[mk] - yk) ** 2)
            line.append(f"damage MSE model {mse_m:.0f} ocean {mse_o:.0f} refit {mse_r:.0f} var {var:.0f} "
                        f"(R2 model {1 - mse_m / var:.3f} ocean {1 - mse_o / var:.3f} refit {1 - mse_r / var:.3f})")
            line.append(f"mean pred model {ed[mk].mean():.1f} ocean {(HGR * ref[mk]).mean():.1f}")
        else:
            line.append(f"damage MSE model {mse_m:.0f} refit {mse_r:.0f} var {var:.0f} (R2 model {1 - mse_m / var:.3f} refit {1 - mse_r / var:.3f})")
        # ranking within a decision: corr of predicted and observed damage
        line.append(f"corr model {np.corrcoef(ed[mk], yk)[0, 1]:.3f} base {np.corrcoef(ref[mk], yk)[0, 1]:.3f}")
        print("\n    ".join(line))
        for s in calib(ph[mk], hk):
            print("      " + s)


def evaluate(model, paths):
    with open(model, "rb") as f:
        m = pickle.load(f)
    D, P, Dc, Pc = load(paths)
    Xd, yd, cd, _ = danger_rows(D, Dc)
    Xp, yp, cp, _ = press_rows(P, Pc)
    report("danger", Xd, yd, cd, *m["danger"], *m["base_d"], Xd[:, 1], HGR)
    report("pressure", Xp, yp, cp, *m["press"], *m["base_p"], Xp[:, 1], None)


def lit(v):
    t = f"{v:.9g}"
    if not any(c in t for c in ".en"):
        t += ".0"
    return t + "f"


def tree_code(pred, names, fn):
    nodes = pred.nodes
    lines = []

    def emit(i, ind):
        nd = nodes[i]
        if nd["is_leaf"]:
            lines.append(" " * ind + f"return {lit(float(nd['value']))};")
            return
        t = float(nd["num_threshold"])
        t32 = np.float32(t)
        if float(t32) > t:
            t32 = np.nextafter(t32, np.float32(-np.inf))
        f = int(nd["feature_idx"])
        lines.append(" " * ind + f"if (x[{f}] <= {lit(float(t32))}) {{ // {names[f]}")
        emit(int(nd["left"]), ind + 4)
        lines.append(" " * ind + "}")
        emit(int(nd["right"]), ind)

    emit(0, 4)
    return f"[[gnu::always_inline]] inline float {fn}(const float* x) {{\n" + "\n".join(lines) + "\n}\n"


def ensemble_code(est, names, fn, sigmoid):
    preds = [p[0] for p in est._predictors]
    out = [tree_code(p, names, f"{fn}_t{i}") for i, p in enumerate(preds)]
    body = " + ".join(f"{fn}_t{i}(x)" for i in range(len(preds)))
    base = float(np.ravel(est._baseline_prediction)[0])
    if sigmoid:
        out.append(f"inline float {fn}(const float* x) {{\n    const float z = {lit(base)} + {body};\n"
                   f"    return 1.0f / (1.0f + std::exp(-z));\n}}\n")
    else:
        out.append(f"inline float {fn}(const float* x) {{ return {lit(base)} + {body}; }}\n")
    return "\n".join(out)


def export(model, header):
    with open(model, "rb") as f:
        m = pickle.load(f)
    parts = ["// Generated by research/reply-model/train.py export: do not edit.", "#pragma once", "#include <algorithm>",
             "#include <cmath>", "", "namespace aph::reply::model {", "namespace detail {"]
    parts.append(ensemble_code(m["danger"][0], DNAMES, "danger_hit", True))
    parts.append(ensemble_code(m["danger"][1], DNAMES, "danger_dmg", False))
    parts.append(ensemble_code(m["press"][0], PNAMES, "press_hit", True))
    parts.append(ensemble_code(m["press"][1], PNAMES, "press_dmg", False))
    parts.append("} // namespace detail")
    parts.append("// Expected damage of e's next turn at p (danger_features), for rows with a blow.")
    parts.append("inline float danger(const float* x) { return detail::danger_hit(x) * std::max(0.0f, detail::danger_dmg(x)); }")
    parts.append("inline float press_hit(const float* x) { return detail::press_hit(x); }")
    parts.append("inline float press_damage(const float* x) { return std::max(0.0f, detail::press_dmg(x)); }")
    parts.append("} // namespace aph::reply::model\n")
    open(header, "w").write("\n".join(parts))
    print(f"{header}: {sum(len(e._predictors) for pair in (m['danger'], m['press']) for e in pair)} trees")


def main():
    a = sys.argv[1:]
    opt = {}
    for k in ("--out", "--trees", "--leaves", "--rows"):
        if k in a:
            i = a.index(k)
            opt[k] = a[i + 1]
            del a[i:i + 2]
    if a[0] == "fit":
        fit(a[1:], opt["--out"], int(opt.get("--trees", 60)), int(opt.get("--leaves", 16)), int(opt.get("--rows", 1_500_000)))
    elif a[0] == "eval":
        evaluate(a[1], a[2:])
    elif a[0] == "export":
        export(a[1], a[2])


if __name__ == "__main__":
    main()


def predict_danger(m, X):
    out = np.zeros(len(X))
    k = X[:, 1] > 0
    if k.any():
        out[k] = m["danger"][0].predict_proba(X[k])[:, 1] * np.maximum(m["danger"][1].predict(X[k]), 0)
    return out


def predict_press(m, X):
    out = np.zeros(len(X))
    k = X[:, 1] > 0
    if k.any():
        out[k] = m["press"][0].predict_proba(X[k])[:, 1] * np.maximum(m["press"][1].predict(X[k]), 0)
    return out


def pairwise(groups, pred, base, y):
    """Over pairs of alternatives in a group whose outcomes differ: the share each predictor orders right."""
    order = np.argsort(groups, kind="stable")
    g, pr, ba, yy = groups[order], pred[order], base[order], y[order]
    right_m = right_b = n = 0.0
    start = 0
    for i in range(1, len(g) + 1):
        if i == len(g) or g[i] != g[start]:
            for a in range(start, i):
                for b in range(a + 1, i):
                    if abs(yy[a] - yy[b]) < 1:
                        continue
                    s = np.sign(yy[a] - yy[b])
                    n += 1
                    right_m += 1.0 if np.sign(pr[a] - pr[b]) == s else 0.5 if pr[a] == pr[b] else 0.0
                    right_b += 1.0 if np.sign(ba[a] - ba[b]) == s else 0.5 if ba[a] == ba[b] else 0.0
            start = i
    return right_m / max(n, 1), right_b / max(n, 1), int(n)


def rank(model, paths):
    """Alternatives at the same decision (build_alt.py rows): does the model order their outcomes?"""
    with open(model, "rb") as f:
        m = pickle.load(f)
    D = np.concatenate([np.load(p)["D"] for p in paths])
    P = np.concatenate([np.load(p)["P"] for p in paths])
    # per (group, enemy): alternatives' danger from e
    Xd, yd = D[:, 5:-1], D[:, -1]
    gd = D[:, 0].astype(np.int64) * 64 + D[:, 4].astype(np.int64)
    pm, pb, n = pairwise(gd, predict_danger(m, Xd), HGR * Xd[:, 1], yd)
    print(f"danger, per enemy: pairs {n}, model right {pm:.3f}, ocean (0.234 x blow) {pb:.3f}")
    # summed over enemies per alternative
    key = D[:, 0].astype(np.int64) * 16 + D[:, 1].astype(np.int64)
    u, inv = np.unique(key, return_inverse=True)
    sp = np.bincount(inv, predict_danger(m, Xd)); sb = np.bincount(inv, HGR * Xd[:, 1]); sy = np.bincount(inv, yd)
    pm, pb, n = pairwise(u // 16, sp, sb, sy)
    print(f"danger, summed per alternative: pairs {n}, model right {pm:.3f}, ocean {pb:.3f}")
    Xp, yp = P[:, 5:-1], P[:, -1]
    gp = P[:, 0].astype(np.int64) * 64 + P[:, 4].astype(np.int64)
    pm, pb, n = pairwise(gp, predict_press(m, Xp), Xp[:, 1], yp)
    print(f"pressure, per target: pairs {n}, model right {pm:.3f}, our strike at d {pb:.3f}")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "rank":
    rank(sys.argv[2], sys.argv[3:])
