"""Export compress.py's logistic GAMs as danger_model.h (PLAN2.md section 3.1), folded as the bot evaluates them, and check
the C++ against Python on held-out rows.

    python3 research/reply-model/export_gam.py export HEADER.h [full.pkl [min5.pkl]]
    python3 research/reply-model/export_gam.py check HEADER.h [full.pkl [min5.pkl]] [--rows 20000]

Each model's hit logit is a sum of trees, each on one feature or a few (one listed pair per branch). Every tree reads at
most one per-tile feature (d, blow, blow_stuns); the rest are fixed for an enemy during our turn. Trees are grouped by
role: fixed (no per-tile feature), d, blow and stuns, and each group is a dense table over its features' cells (a
feature's cells are cut by the union of its thresholds over every tree). The bot sums the fixed tables once per enemy
(z), folds the d tables into td[d] (d 0-15) and the stuns table into ts[0/1], and keeps an offset into each blow table;
a query is then one search over blow's thresholds, a few loads and a sigmoid table.
"""
import os
import pickle
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compress  # noqa: E402
import train  # noqa: E402

for _k in ("Gam", "Coarse", "Table", "Flat"):
    setattr(sys.modules["__main__"], _k, getattr(compress, _k))

C = compress.C
N = train.DNAMES
TILE = ("d", "blow", "blow_stuns")
FULL = f"{C}/r3_gam_Appairs_cap.pkl"
MIN5 = f"{C}/r5_gam_min5_cap.pkl"
DMAX = 8  # td[] entries: d 0..7, clamped (blow > 0 lies within a strike reach, at most 6)
SIG_LO, SIG_HI, SIG_N = -10.0, 10.0, 1024  # sigmoid table over [lo, hi], linear between entries


def f32_down(t):
    """The largest float32 <= t: for a float32 x, x <= t exactly when x <= f32_down(t)."""
    v = np.float32(t)
    if float(v) > t:
        v = np.nextafter(v, np.float32(-np.inf))
    return float(v)


def trees_of(g):
    """[(feature names of the tree, predictor)] for a fitted Gam (indices into g.names)."""
    out = []
    for p in g.clf._predictors:
        nodes = p[0].nodes
        feats = tuple(sorted(set(int(f) for f in nodes["feature_idx"][nodes["is_leaf"] == 0])))
        out.append((tuple(g.names[f] for f in feats), p[0]))
    return out


def tree_predict(nodes, X):
    """A tree's leaf values at the rows of X (x <= threshold goes left; no missing values)."""
    at = np.zeros(len(X), dtype=np.int64)
    while True:
        inner = ~nodes["is_leaf"][at].astype(bool)
        if not inner.any():
            return nodes["value"][at]
        i = np.nonzero(inner)[0]
        nd = nodes[at[i]]
        left = X[i, nd["feature_idx"].astype(np.int64)] <= nd["num_threshold"]
        at[i] = np.where(left, nd["left"], nd["right"])


class Model:
    def __init__(self, name, g):
        self.name, self.g = name, g
        self.base = float(np.ravel(g.clf._baseline_prediction)[0])
        self.k = float(g.k)
        trees = trees_of(g)
        # Union thresholds per feature (in the 48-slot layout), as float32 rounded down.
        th = {}
        for feats, pred in trees:
            nodes = pred.nodes
            for nd in nodes[nodes["is_leaf"] == 0]:
                th.setdefault(g.names[int(nd["feature_idx"])], set()).add(float(nd["num_threshold"]))
        self.th = {f: np.array(sorted(v)) for f, v in th.items()}
        self.th32 = {f: np.array(sorted(set(f32_down(t) for t in v)), dtype=np.float32) for f, v in self.th.items()}
        # Groups by role: the per-tile feature (or none) with the union of the fixed features of its trees.
        groups = {}
        for feats, pred in trees:
            tile = [f for f in feats if f in TILE]
            assert len(tile) <= 1, feats
            role = tile[0] if tile else None
            groups.setdefault(role, []).append((feats, pred))
        self.groups = []  # (role, features with the per-tile one last, table)
        for role, ts in groups.items():
            # One group per distinct feature set, each tree in the smallest superset (kept apart: a merged table is a product).
            sets = sorted({f for f, _ in ts}, key=len, reverse=True)
            maximal = [s for s in sets if not any(set(s) < set(t) for t in sets)]
            parts = {}
            for feats, pred in ts:
                home = min((s for s in maximal if set(feats) <= set(s)), key=len)
                parts.setdefault(home, []).append(pred)
            for s, preds in parts.items():
                gf = [f for f in s if f != role] + ([role] if role else [])
                self.groups.append((role, gf, self.table(gf, preds)))

    def ncell(self, f):
        return len(self.th.get(f, [])) + 1

    def reps(self, f):
        t = self.th.get(f, np.array([]))
        if len(t) == 0:
            return np.array([0.0])
        mids = (t[:-1] + t[1:]) / 2
        return np.r_[t[0] - 1.0, mids, t[-1] + 1.0]

    def table(self, feats, preds):
        grids = np.meshgrid(*[self.reps(f) for f in feats], indexing="ij")
        X = np.zeros((grids[0].size, len(self.g.names)))
        for f, gr in zip(feats, grids):
            X[:, self.g.names.index(f)] = gr.ravel()
        tot = np.zeros(len(X))
        for p in preds:
            tot += tree_predict(p.nodes, X)
        return tot.reshape(grids[0].shape)

    # Python evaluation of the export, for the check: the logit from the tables.
    def cell(self, f, x):
        t = self.th.get(f, np.array([]))
        return np.searchsorted(t, x, side="left")

    def logit(self, X):
        s = np.full(len(X), self.base)
        for role, feats, tab in self.groups:
            idx = tuple(self.cell(f, X[:, N.index(f)]) for f in feats)
            s += tab[idx]
        return s


def lit(v):
    return train.lit(float(v))


def arr(vals, per=8):
    vals = [lit(v) for v in vals]
    rows = [", ".join(vals[i:i + per]) for i in range(0, len(vals), per)]
    return "{\n        " + ",\n        ".join(rows) + "}" if vals else "{}"


def emit(m):
    """The model's namespace: thresholds, tables, fold() and the per-query logit."""
    L = [f"namespace {m.name} {{", f"inline constexpr float base = {lit(m.base)};", f"inline constexpr float k = {lit(m.k)};"]
    feats = sorted(m.th32, key=N.index)
    for f in feats:
        L.append(f"inline constexpr float t_{f}[] = {arr(m.th32[f])}; // {len(m.th32[f])} thresholds")
    # A feature's cell: how many thresholds lie below x (x <= t goes left).
    L.append("template <std::size_t n> [[gnu::always_inline]] inline int cell(const float (&t)[n], float x) {")
    L.append("    int lo = 0, hi = static_cast<int>(n);")
    L.append("    while (lo < hi) {")
    L.append("        const int mid = (lo + hi) >> 1;")
    L.append("        if (t[mid] < x) lo = mid + 1;")
    L.append("        else hi = mid;")
    L.append("    }")
    L.append("    return lo;")
    L.append("}")
    blow_groups = []
    for gi, (role, gf, tab) in enumerate(m.groups):
        L.append(f"// group {gi}: {role or 'fixed'} over {', '.join(gf)} ({'x'.join(str(s) for s in tab.shape)})")
        L.append(f"inline constexpr float g{gi}[] = {arr(tab.ravel())};")
        if role == "blow":
            blow_groups.append(gi)
    # The blow tables are cut by blow's union thresholds (blow is last, so a row is contiguous).
    L.append(f"inline constexpr int blow_groups = {len(blow_groups)};")
    L.append(f"inline constexpr int blow_cells = {m.ncell('blow')};")
    L.append("struct Folded {")
    L.append("    float z;")
    L.append(f"    float td[{DMAX}];")
    L.append("    float ts[2];")
    L.append(f"    int boff[{max(1, len(blow_groups))}];")
    L.append("};")

    def index_expr(gf, tab, fixed_vals, last=None):
        # Row-major offset with the per-tile feature (if any) last, given C++ expressions for each cell.
        terms = []
        stride = 1
        dims = list(tab.shape)
        for j in range(len(gf) - 1, -1, -1):
            e = last if (last is not None and j == len(gf) - 1) else fixed_vals[gf[j]]
            terms.append(f"{stride} * ({e})" if stride != 1 else f"({e})")
            stride *= dims[j]
        return " + ".join(reversed(terms))

    # fold(x): x in the 48-slot layout, its fixed slots filled.
    L.append("// x: the 48-slot danger_features layout; only the fixed slots are read.")
    L.append("inline void fold(const float* x, Folded& f) {")
    for fe in sorted({f for _, gf, _ in m.groups for f in gf if f not in TILE}, key=N.index):
        L.append(f"    const int c_{fe} = cell(t_{fe}, x[{N.index(fe)}]); // {fe}")
    cv = {fe: f"c_{fe}" for fe in N}
    zt = [f"g{gi}[{index_expr(gf, tab, cv)}]" for gi, (role, gf, tab) in enumerate(m.groups) if role is None]
    L.append(f"    f.z = base{''.join(' + ' + t for t in zt)};")
    dg = [(gi, gf, tab) for gi, (role, gf, tab) in enumerate(m.groups) if role == "d"]
    L.append(f"    for (int d = 0; d < {DMAX}; ++d) {{")
    if dg:
        L.append("        const int c_d = cell(t_d, static_cast<float>(d));")
        L.append(f"        f.td[d] = {' + '.join(f'g{gi}[{index_expr(gf, tab, cv, last='c_d')}]' for gi, gf, tab in dg)};")
    else:
        L.append("        f.td[d] = 0;")
    L.append("    }")
    sg = [(gi, gf, tab) for gi, (role, gf, tab) in enumerate(m.groups) if role == "blow_stuns"]
    for s in (0, 1):
        if sg:
            L.append(f"    {{ const int c_blow_stuns = cell(t_blow_stuns, {s}.0f);")
            L.append(f"      f.ts[{s}] = {' + '.join(f'g{gi}[{index_expr(gf, tab, cv, last='c_blow_stuns')}]' for gi, gf, tab in sg)}; }}")
        else:
            L.append(f"    f.ts[{s}] = 0;")
    for j, gi in enumerate(blow_groups):
        _, gf, tab = m.groups[gi]
        assert tab.shape[-1] == m.ncell("blow")
        L.append(f"    f.boff[{j}] = {index_expr(gf, tab, cv, last='0')};")
    L.append("}")
    L.append("[[gnu::always_inline]] inline int blow_cell(float blow) { return cell(t_blow, blow); }")
    L.append("// The blow tables' sum at blow cell b.")
    L.append("[[gnu::always_inline]] inline float blow_term(const Folded& f, int b) {")
    L.append(f"    return {' + '.join(f'g{gi}[f.boff[{j}] + b]' for j, gi in enumerate(blow_groups)) or '0.0f'};")
    L.append("}")
    L.append("[[gnu::always_inline]] inline float logit(const Folded& f, int d, float blow, bool stuns) {")
    L.append(f"    return f.z + f.td[d < 0 ? 0 : d > {DMAX - 1} ? {DMAX - 1} : d] + blow_term(f, blow_cell(blow)) + f.ts[stuns ? 1 : 0];")
    L.append("}")
    L.append(f"}} // namespace {m.name}")
    return L


def sigmoid_table():
    xs = np.linspace(SIG_LO, SIG_HI, SIG_N + 1)
    return 1 / (1 + np.exp(-xs))


def export(header, full, min5, meta):
    models = [Model("full", pickle.load(open(full, "rb"))), Model("min5", pickle.load(open(min5, "rb")))]
    L = ["// Generated by research/reply-model/export_gam.py: do not edit.",
         f"// full: {os.path.basename(full)}; min5: {os.path.basename(min5)}. {meta}",
         "// P(a visible enemy's next turn hits us at a tile) as a logistic GAM on danger_features (combat/reply.cc's",
         "// layout); expected damage = k x min(blow, our health + shield, at least 1) x p.",
         "#pragma once", "#include <cstddef>", "", "namespace aph::danger_model {", ""]
    L.append(f"inline constexpr float sig_lo = {lit(SIG_LO)}, sig_hi = {lit(SIG_HI)};")
    L.append(f"inline constexpr int sig_n = {SIG_N};")
    L.append(f"inline constexpr float sig[] = {arr(sigmoid_table())};")
    L.append("[[gnu::always_inline]] inline float sigmoid(float z) {")
    L.append("    if (!(z > sig_lo)) return sig[0];")
    L.append("    if (z >= sig_hi) return sig[sig_n];")
    L.append(f"    const float u = (z - sig_lo) * {lit(SIG_N / (SIG_HI - SIG_LO))};")
    L.append("    const int i = static_cast<int>(u);")
    L.append("    return sig[i] + (sig[i + 1] - sig[i]) * (u - static_cast<float>(i));")
    L.append("}")
    L.append("")
    for m in models:
        L += emit(m)
        L.append("")
    L.append("} // namespace aph::danger_model")
    open(header, "w").write("\n".join(L) + "\n")
    for m in models:
        print(f"{m.name}: base {m.base:.4f} k {m.k:.4f}; groups:",
              "; ".join(f"{r or 'fixed'}[{','.join(gf)}] {'x'.join(map(str, t.shape))}" for r, gf, t in m.groups))
    return models


def check(header, full, min5, rows):
    va = np.load(f"{C}/val.npy")
    rng = np.random.default_rng(1)
    X = va[rng.choice(len(va), min(rows, len(va)), replace=False), 4:-1].astype(np.float32)
    d = tempfile.mkdtemp()
    src = os.path.join(d, "t.cc")
    open(src, "w").write(f'''#include <cstdio>
#include <algorithm>
#include "{os.path.abspath(header)}"
using namespace aph::danger_model;
int main() {{
    int n, k; float x[64];
    if (scanf("%d %d", &n, &k) != 2) return 1;
    for (int i = 0; i < n; ++i) {{
        for (int j = 0; j < k; ++j) if (scanf("%a", &x[j]) != 1) return 2;
        const int dd = static_cast<int>(x[0]);
        full::Folded f; full::fold(x, f);
        min5::Folded g; min5::fold(x, g);
        const float zf = full::logit(f, dd, x[1], x[2] > 0.5f), zg = min5::logit(g, dd, x[1], x[2] > 0.5f);
        const float m = std::min(x[1], std::max(x[12], 1.0f));
        printf("%a %a %a %a\\n", zf, sigmoid(zf), zg, full::k * m * sigmoid(zf));
    }}
}}
''')
    subprocess.run(["clang++", "-O1", "-std=c++20", src, "-o", os.path.join(d, "t")], check=True)
    inp = [f"{len(X)} {X.shape[1]}"] + [" ".join(float(v).hex() for v in row) for row in X]
    out = subprocess.run([os.path.join(d, "t")], input="\n".join(inp), capture_output=True, text=True, check=True).stdout.split()
    c = np.array([float.fromhex(v) for v in out]).reshape(-1, 4)
    gf, gm = pickle.load(open(full, "rb")), pickle.load(open(min5, "rb"))
    Xd = X.astype(np.float64)
    zf = gf.clf._raw_predict(Xd[:, gf.ix])[:, 0] if hasattr(gf.clf, "_raw_predict") else None
    zm = gm.clf._raw_predict(Xd[:, gm.ix])[:, 0]
    pf = gf.hit(Xd)
    df = gf.danger(Xd)
    print(f"rows {len(X)}; d range {X[:, 0].min():.0f}-{X[:, 0].max():.0f}")
    print(f"full logit max abs diff {np.abs(c[:, 0] - zf).max():.2e}; p {np.abs(c[:, 1] - pf).max():.2e}; danger {np.abs(c[:, 3] - df).max():.2e}"
          f" (mean {df.mean():.2f})")
    print(f"min5 logit max abs diff {np.abs(c[:, 2] - zm).max():.2e}")
    # Python's table evaluation too, which the bot's fold mirrors.
    mf = Model("full", gf)
    print(f"full tables vs sklearn logit max abs diff {np.abs(mf.logit(Xd) - zf).max():.2e}")


def main():
    a = sys.argv[1:]
    rows = 20000
    if "--rows" in a:
        i = a.index("--rows")
        rows = int(a[i + 1])
        del a[i:i + 2]
    cmd, header = a[0], a[1]
    full = a[2] if len(a) > 2 else FULL
    min5 = a[3] if len(a) > 3 else MIN5
    if cmd == "export":
        export(header, full, min5, "Trained on the phase-1 lab rows (oo, oa, ao; 1.2M train rows).")
    else:
        check(header, full, min5, rows)


if __name__ == "__main__":
    main()
