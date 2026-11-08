"""Cheap stand-ins for the reply model's danger term, judged against the full model (m1) and the lean one on
held-out rows (PLAN2.md, question 1).

    python3 research/reply-model/compress.py cache            # danger rows (blow > 0) to replays/combatlab/reply/compress/
    python3 research/reply-model/compress.py run [NAMES...]   # fit and score the candidates (all by default)

Every candidate is danger = blow x p(x) x k, with p a hit probability (a logistic GAM: a sum of 1-D, or a few 2-D,
step functions, i.e. lookup tables) and k = E[damage / blow | hit] fitted on the training rows, unless it says
otherwise. Scores on the held-out frames: hit log loss, damage R2 (all and by opponent), mean, and the share of
alternatives of one decision (build_alt.py rows) ordered right, per enemy and summed per alternative.
"""
import pickle
import sys
import time

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import train  # noqa: E402

D = "replays/combatlab/reply/data"
C = "replays/combatlab/reply/compress"
N = train.DNAMES
HGR = train.HGR

# Cost tiers (PLAN2.md): A is free at a query (blow, d) or fixed per enemy for the turn; B is per tile and shared by
# every enemy (or a short loop over mates); C needs Reach::sources at the tile, a second pass like Reach::at.
TIER_A = ["blow", "blow_stuns", "d", "strike_at", "e_turns", "e_channel", "e_type", "e_ranged", "my_type", "my_ranged", "e_hp",
          "e_hp_frac", "e_str", "my_hp", "my_hp_frac", "e_dash_ready", "e_cd0", "e_cd1", "n_alt", "alt_min_hp_frac", "alt_best",
          "alt_gems", "e_hurt", "e_stun_pending", "e_gems", "my_gems", "n_vis", "n_mates", "e_bush", "e_spawn_steps"]
TIER_B = ["mate_hp_near", "foe_hp_near", "mates_near", "foes_near", "p_bush", "moved", "e_ttd", "our_dmg_on_e", "my_strike_on_e",
          "camp_p", "p_open"]
TIER_C = ["n_src", "n_src_basic", "n_src_safe", "src_here", "n_src_nocamp", "n_src_free", "e_in_zone"]
assert sorted(TIER_A + TIER_B + TIER_C) == sorted(N)


def cache():
    rng = np.random.default_rng(0)
    tr, trc = [], []
    for k, cfg in enumerate(["oo", "oa", "ao"]):
        A = np.load(f"{D}/tr-{cfg}.npz")["D"]
        A = A[A[:, 5] > 0]
        tr.append(A), trc.append(np.full(len(A), k, np.int8))
        print(cfg, "train danger rows", len(A), flush=True)
    tr, trc = np.concatenate(tr), np.concatenate(trc)
    i = rng.choice(len(tr), min(len(tr), 2_000_000), replace=False)
    np.save(f"{C}/train.npy", tr[i]), np.save(f"{C}/train_cfg.npy", trc[i])
    va, vac = [], []
    for k, cfg in enumerate(["oo", "oa", "ao"]):
        A = np.load(f"{D}/va-{cfg}.npz")["D"]
        A = A[A[:, 5] > 0]
        va.append(A), vac.append(np.full(len(A), k, np.int8))
    np.save(f"{C}/val.npy", np.concatenate(va)), np.save(f"{C}/val_cfg.npy", np.concatenate(vac))
    alt = np.concatenate([np.load(f"{D}/alt-va-{c}.npz")["D"] for c in ("oo", "oa", "ao")])
    np.save(f"{C}/alt.npy", alt)
    print("cached", len(i), "train,", sum(len(v) for v in va), "val,", len(alt), "alternative rows")


def idx(names):
    return [N.index(n) for n in names]


class Gam:
    """danger = blow x p(x) x k; p a logistic GAM (interaction_cst: one feature, or one listed pair, per tree)."""

    def __init__(self, names, pairs=(), trees=300, leaves=8, k_names=None, lr=0.1, rescale=False, weigh=False, free=False, cap=False):
        self.names, self.pairs, self.trees, self.leaves, self.k_names, self.lr = list(names), list(pairs), trees, leaves, k_names, lr
        self.rescale, self.weigh, self.free = rescale, weigh, free  # free: unconstrained trees (a small boosted model)
        self.cap = cap  # cap: the multiplier is min(blow, our health and shield), what a hit can take

    def fit(self, X, y):
        self.ix = idx(self.names)
        groups = [[i] for i in range(len(self.ix))]
        for a, b in self.pairs:
            groups.append([self.names.index(a), self.names.index(b)])
        hit = y > 0.5
        self.clf = HistGradientBoostingClassifier(max_iter=self.trees, max_leaf_nodes=self.leaves, learning_rate=self.lr, min_samples_leaf=200,
                                                  l2_regularization=1.0, early_stopping=False, random_state=0, interaction_cst=None if self.free else groups)
        # weigh: each row by its blow, so p is calibrated in damage rather than in hits
        self.clf.fit(X[:, self.ix], hit, sample_weight=X[:, 1] / X[:, 1].mean() if self.weigh else None)
        b = self.mult(X)
        r = y[hit] / b[hit]
        self.k = float((b[hit] * y[hit]).sum() / (b[hit] ** 2).sum())  # least-squares damage multiple of blow
        if self.k_names:
            self.kx = idx(self.k_names)
            self.kreg = HistGradientBoostingRegressor(max_iter=100, max_leaf_nodes=8, learning_rate=0.1, min_samples_leaf=200,
                                                      l2_regularization=1.0, early_stopping=False, random_state=0,
                                                      interaction_cst=[[i] for i in range(len(self.kx))])
            self.kreg.fit(X[hit][:, self.kx], r, sample_weight=b[hit] ** 2)
        if self.rescale and not self.k_names:
            # rescale: k is the least-squares multiple of blow x p (unbiased in damage) rather than E[damage / blow | hit]
            q = self.mult(X) * self.hit(X)
            self.k = float((q * y).sum() / (q * q).sum())
        return self

    def mult(self, X):
        return np.minimum(X[:, 1], np.maximum(X[:, 12], 1)) if getattr(self, "cap", False) else X[:, 1]

    def hit(self, X):
        return self.clf.predict_proba(X[:, self.ix])[:, 1]

    def danger(self, X):
        k = np.maximum(self.kreg.predict(X[:, self.kx]), 0) if self.k_names else self.k
        return self.mult(X) * self.hit(X) * k

    def tables(self):
        """Distinct steps per 1-D function and cells per 2-D one: the lookup-table sizes."""
        out = {}
        for p in self.clf._predictors:
            nodes = p[0].nodes
            feats = tuple(sorted(set(int(f) for f in nodes["feature_idx"][nodes["is_leaf"] == 0])))
            th = out.setdefault(feats, [set() for _ in feats])
            for nd in nodes[nodes["is_leaf"] == 0]:
                th[feats.index(int(nd["feature_idx"]))].add(float(nd["num_threshold"]))
        return {tuple(self.names[f] for f in k): [len(s) + 1 for s in v] for k, v in out.items()}


class Coarse:
    """A fitted Gam with each 1-D function re-binned to at most `bins` quantile bins (what a 16-entry table holds)."""

    def __init__(self, gam, X, bins=16):
        self.g, self.bins = gam, bins
        Z = X[:, gam.ix]
        base = np.zeros(len(Z))
        self.edges, self.vals = [], []
        # each feature's function: the raw score with that column varied and the others at a fixed row, minus the base
        ref = np.tile(Z[:1], (1, 1))
        raw0 = gam.clf._raw_predict(ref)[0, 0]
        for j in range(Z.shape[1]):
            v = Z[:, j]
            q = np.unique(np.quantile(v, np.linspace(0, 1, bins + 1)[1:-1]))
            b = np.searchsorted(q, v, side="right")
            R = np.repeat(ref, len(v), axis=0)
            R[:, j] = v
            f = gam.clf._raw_predict(R)[:, 0] - raw0
            vals = np.array([f[b == k].mean() if (b == k).any() else 0.0 for k in range(len(q) + 1)])
            self.edges.append(q), self.vals.append(vals)
        self.raw0 = raw0

    def hit(self, X):
        Z = X[:, self.g.ix]
        s = np.full(len(Z), self.raw0)
        for j in range(Z.shape[1]):
            s += self.vals[j][np.searchsorted(self.edges[j], Z[:, j], side="right")]
        return 1 / (1 + np.exp(-s))

    def danger(self, X):
        return self.g.mult(X) * self.hit(X) * self.g.k


class Table:
    """danger = blow x t[cell]: a least-squares multiple of blow per cell of a few integer features (shrunk to the global one)."""

    def __init__(self, names, clip=None):
        self.names, self.clip = names, clip or {}

    def cell(self, X):
        key = np.zeros(len(X), np.int64)
        for n in self.names:
            v = X[:, N.index(n)]
            lo, hi = self.clip.get(n, (0, 9))
            key = key * 16 + np.clip(np.round(v), lo, hi).astype(np.int64)
        return key

    def fit(self, X, y):
        k = self.cell(X)
        b = X[:, 1]
        g = (b * y).sum() / (b * b).sum()
        u, inv = np.unique(k, return_inverse=True)
        num, den = np.bincount(inv, b * y), np.bincount(inv, b * b)
        w = 2000 * 150.0 ** 2  # shrinkage: about 2000 rows of a typical blow
        self.t = dict(zip(u.tolist(), ((num + w * g) / (den + w)).tolist()))
        hit = (y > 0.5).astype(float)
        self.h = dict(zip(u.tolist(), ((np.bincount(inv, hit) + 200 * hit.mean()) / (np.bincount(inv) + 200)).tolist()))
        self.g = g
        return self

    def danger(self, X):
        return X[:, 1] * np.array([self.t.get(c, self.g) for c in self.cell(X).tolist()])

    def hit(self, X):
        return np.array([self.h.get(c, 0.32) for c in self.cell(X).tolist()])


class Full:
    def __init__(self, path):
        self.m = pickle.load(open(path, "rb"))

    def hit(self, X):
        return self.m["danger"][0].predict_proba(X)[:, 1]

    def danger(self, X):
        return self.hit(X) * np.maximum(self.m["danger"][1].predict(X), 0)


class Lean:
    def __init__(self, path):
        self.m = pickle.load(open(path, "rb"))

    def danger(self, X):
        return np.maximum(self.m["est"].predict(X[:, self.m["idx"]]), 0)


class Flat:
    def __init__(self, k):
        self.k = k

    def danger(self, X):
        return self.k * X[:, 1]

    def hit(self, X):
        return np.full(len(X), HGR)


def pairwise_fast(groups, pred, base, y):
    return train.pairwise(groups, pred, base, y)


def score(name, m, Xv, yv, cv, alt, fit_s=0.0):
    ed = m.danger(Xv)
    var = np.var(yv)
    r2 = 1 - np.mean((ed - yv) ** 2) / var
    by = []
    for k in range(3):
        mk = cv == k
        by.append(1 - np.mean((ed[mk] - yv[mk]) ** 2) / np.var(yv[mk]))
    ll = ""
    if hasattr(m, "hit"):
        ll = f"{train.logloss(m.hit(Xv), (yv > 0.5).astype(float)):.4f}"
    Xa, ya = alt[:, 5:-1], alt[:, -1]
    pa = np.zeros(len(Xa))
    ka = Xa[:, 1] > 0
    pa[ka] = m.danger(Xa[ka])
    g = alt[:, 0].astype(np.int64) * 64 + alt[:, 4].astype(np.int64)
    pe, pb, n = pairwise_fast(g, pa, HGR * Xa[:, 1], ya)
    key = alt[:, 0].astype(np.int64) * 16 + alt[:, 1].astype(np.int64)
    u, inv = np.unique(key, return_inverse=True)
    ps, _, ns = pairwise_fast(u // 16, np.bincount(inv, pa), np.bincount(inv, HGR * Xa[:, 1]), np.bincount(inv, ya))
    line = (f"{name:28s} logloss {ll:>6s}  R2 {r2:.3f} (oo {by[0]:.3f} oa {by[1]:.3f} ao {by[2]:.3f})  mean {ed.mean():5.1f}/{yv.mean():.1f}"
            f"  order/enemy {pe:.3f}  order/alt {ps:.3f}  fit {fit_s:.0f}s")
    print(line, flush=True)
    return {"name": name, "logloss": ll, "r2": r2, "by": by, "mean": float(ed.mean()), "order_enemy": pe, "order_alt": ps}


def candidates(Xt):
    top = ["blow", "e_turns", "mate_hp_near", "src_here", "n_src", "my_hp", "e_channel", "foe_hp_near", "e_ttd", "e_hp_frac",
           "e_dash_ready", "e_hp", "e_str", "e_type", "alt_min_hp_frac", "d", "blow_stuns", "alt_best", "n_src_safe", "my_hp_frac",
           "n_src_basic", "n_alt", "e_cd1", "p_bush", "e_hurt", "my_type", "e_gems", "e_ranged"]
    lean_feats = pickle.load(open("replays/combatlab/reply/lean-12x32.pkl", "rb"))["names"]
    a = [n for n in lean_feats if n in TIER_A]
    ab = [n for n in lean_feats if n in TIER_A + TIER_B]
    a6 = ["blow", "d", "e_turns", "e_type", "my_hp", "e_channel"]
    kn = ["blow", "my_hp", "e_turns", "e_type", "d", "blow_stuns"]
    pairs_a = [("d", "e_type"), ("d", "e_dash_ready"), ("blow", "e_turns"), ("e_turns", "e_type"), ("blow", "my_hp")]
    pairs_c = [("d", "e_type"), ("e_turns", "src_here"), ("d", "e_dash_ready"), ("blow", "e_turns"), ("n_src_basic", "e_ranged")]
    return {
        "table e_turns": lambda: Table(["e_turns"], {"e_turns": (0, 2)}),
        "table e_turns,d": lambda: Table(["e_turns", "d"], {"e_turns": (0, 2), "d": (1, 6)}),
        "table e_turns,d,e_type": lambda: Table(["e_turns", "d", "e_type"], {"e_turns": (0, 2), "d": (1, 6), "e_type": (0, 15)}),
        "gam A(lean) 1-D": lambda: Gam(a),
        "gam A+B(lean) 1-D": lambda: Gam(ab),
        "gam lean 1-D": lambda: Gam(lean_feats),
        "gam all48 1-D": lambda: Gam(N),
        "gam A+pairs": lambda: Gam(a, [("d", "e_type"), ("d", "e_dash_ready"), ("blow", "e_turns")]),
        "gam A+B+pairs": lambda: Gam(ab, [("d", "e_type"), ("d", "e_dash_ready"), ("blow", "e_turns")]),
        "gam lean+pairs": lambda: Gam(lean_feats, pairs_c),
        "gam lean+pairs+k": lambda: Gam(lean_feats, pairs_c, k_names=["blow", "d", "e_type", "blow_stuns", "my_hp"]),
        "gam top8 1-D": lambda: Gam(top[:8]),
        "gam top12 1-D": lambda: Gam(top[:12]),
        "r2 gam A rescale": lambda: Gam(a, rescale=True),
        "r2 gam A weigh": lambda: Gam(a, weigh=True, rescale=True),
        "r2 gam A+pairs rescale": lambda: Gam(a, [("d", "e_type"), ("d", "e_dash_ready"), ("blow", "e_turns"), ("e_turns", "e_type"), ("blow", "my_hp")], rescale=True),
        "r2 gam lean rescale": lambda: Gam(lean_feats, rescale=True),
        "r2 gam lean+pairs rescale": lambda: Gam(lean_feats, pairs_c + [("blow", "my_hp")], rescale=True),
        "r2 gam A6 rescale": lambda: Gam(["blow", "d", "e_turns", "e_type", "my_hp", "e_channel"], rescale=True),
        "r2 gam A6+pairs rescale": lambda: Gam(["blow", "d", "e_turns", "e_type", "my_hp", "e_channel"], [("d", "e_type"), ("blow", "e_turns"), ("e_turns", "e_type")], rescale=True),
        "r2 trees A 8x8": lambda: Gam(a, trees=8, leaves=8, lr=0.5, rescale=True, free=True),
        "r2 trees lean 8x8": lambda: Gam(lean_feats, trees=8, leaves=8, lr=0.5, rescale=True, free=True),
        "r3 gam A+pairs cap": lambda: Gam(a, pairs_a, cap=True),
        "r3 gam A+pairs cap k": lambda: Gam(a, pairs_a, cap=True, k_names=kn),
        "r3 gam A6+pairs cap k": lambda: Gam(a6, [("d", "e_type"), ("blow", "e_turns"), ("e_turns", "e_type")], cap=True, k_names=kn),
        "r3 gam lean+pairs cap k": lambda: Gam(lean_feats, pairs_c + [("blow", "my_hp")], cap=True, k_names=kn),
        "r3 trees A 8x8 cap k": lambda: Gam(a, trees=8, leaves=8, lr=0.5, free=True, cap=True, k_names=kn),
        "r4 gam A per-enemy cap": lambda: Gam([n for n in a if n not in ("d", "blow", "blow_stuns")], [("e_turns", "e_type")], cap=True),
        "r4 refit cap": lambda: Gam(["e_turns"], trees=1, leaves=2, lr=1e-6, cap=True),
        "r5 gam min5 cap": lambda: Gam(["d", "blow", "blow_stuns", "e_turns", "e_type"], [("d", "e_type"), ("blow", "e_turns"), ("e_turns", "e_type")], cap=True),
        "r5 gam min7 cap": lambda: Gam(["d", "blow", "blow_stuns", "e_turns", "e_type", "my_hp", "e_dash_ready"],
                                       [("d", "e_type"), ("blow", "e_turns"), ("e_turns", "e_type"), ("blow", "my_hp"), ("d", "e_dash_ready")], cap=True),
        "gam top12+pairs": lambda: Gam(top[:12] + ["d"], [("d", "e_type"), ("e_turns", "src_here"), ("blow", "e_turns")]),
    }


def run(names):
    Xt_all = np.load(f"{C}/train.npy")
    Xt, yt = Xt_all[:, 4:-1], Xt_all[:, -1]
    va = np.load(f"{C}/val.npy")
    Xv, yv, cv = va[:, 4:-1], va[:, -1], np.load(f"{C}/val_cfg.npy")
    alt = np.load(f"{C}/alt.npy")
    print(f"train {len(yt)}, val {len(yv)}, alt {len(alt)}", flush=True)
    res = []
    if not names or "base" in names:
        res.append(score("ocean 0.234 x blow", Flat(HGR), Xv, yv, cv, alt))
        k = float((Xt[:, 1] * yt).sum() / (Xt[:, 1] ** 2).sum())
        res.append(score(f"refit {k:.3f} x blow", Flat(k), Xv, yv, cv, alt))
        res.append(score("full m1 (4.6k splits)", Full("replays/combatlab/reply/m1.pkl"), Xv, yv, cv, alt))
        res.append(score("lean 12x32", Lean("replays/combatlab/reply/lean-12x32.pkl"), Xv, yv, cv, alt))
    cands = candidates(Xt)
    rows = 1_200_000
    for name, make in cands.items():
        if names and not any(name.startswith(n) for n in names):
            continue
        t = time.time()
        m = make().fit(Xt[:rows], yt[:rows])
        res.append(score(name, m, Xv, yv, cv, alt, time.time() - t))
        if isinstance(m, Gam):
            tabs = m.tables()
            print("    tables:", "; ".join(f"{'x'.join(k)} {v}" for k, v in sorted(tabs.items(), key=lambda kv: -np.prod(kv[1]))[:14]),
                  f"| {len(tabs)} tables, {sum(int(np.prod(v)) for v in tabs.values())} cells", flush=True)
            if not m.pairs and not m.k_names and not m.free:
                res.append(score(name + " (16 bins)", Coarse(m, Xt[:200_000]), Xv, yv, cv, alt))
            pickle.dump(m, open(f"{C}/{name.replace(' ', '_').replace(',', '-').replace('(', '').replace(')', '').replace('+', 'p')}.pkl", "wb"))
    pickle.dump(res, open(f"{C}/results-{int(time.time())}.pkl", "wb"))


if __name__ == "__main__":
    if sys.argv[1] == "cache":
        cache()
    else:
        run(sys.argv[2:])
