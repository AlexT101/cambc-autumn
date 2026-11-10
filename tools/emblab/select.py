"""Selection rules over the doubly robust sums dfit.mjs --dr / --mapdr dumps (<model>.drsums.bin, .mapsums.bin),
scored by cross-fitting over its map folds: each fold's selection is made on the other folds and scored on it.

    py tools/emblab/select.py MODEL.json                        # the rules' cross-fitted gains, per opponent kind
    py tools/emblab/select.py MODEL.json --write RULE --out sel.json   # RULE's selection on all folds (candidate.py --key RULE reads it)
    py tools/emblab/select.py MODEL.json --maps                 # map-keyed rules too (needs --mapdr's sums)

A cell is (pick count, type, ordinal); a candidate is a fixed arm (the current logic where it is not drawable) or
the current logic itself; D is a candidate's doubly robust gain over the base in one decision. Rules:

    cell-zZ          per cell, the candidate with the best mean D - Z se, if positive (dfit's class 0)
    tb-zZ, tk-zZ, t-zZ   the same on pooled cells: type x ordinal bucket, type x ordinal, type (one arm for the group)
    hier-zZ-tT       per cell, mean D shrunk towards the rest of its type x bucket group's (heterogeneity sd T points)
    tb-zZ+cell-zY    the group rule, then a cell's own candidate where it clears Y se by itself
    FEAT@B:RULE      (--maps) RULE separately on the maps below and from cut B (1-7) of FEAT's eight quantile bins
    FEAT@B~sS:tb-zZ  (--maps) the same, each side's mean shrunk towards both sides' (heterogeneity sd S points)

Each line gives the formula's se and, in brackets, the se from the spread of the five folds' gains (4 degrees of
freedom, rough but honest: the folds are disjoint sets of maps). Trust the larger. Round 4's mid-run fit read tb-z2 at
+0.149 ± 0.050; the same selection read -0.02 ± 0.09 on later games and lost 1.9 points in the A/B. `--on` scores
MODEL's selections on another fit's games (later, independent ones): the replication to require before any A/B.

Gains are win points per decision over all decisions; a team makes ~28 below ordinal 12 (round 2: +0.08 a decision
was +2.3 points in the A/B). Comparing many rules on these numbers is optimistic: state the few to try first, and
judge the winners by A/B on held-out suites."""
import argparse, json, re, sys
from pathlib import Path

import numpy as np

KC = lambda k: k if k < 3 else 3 if k < 6 else 4


class Sums:
    def __init__(self, model):
        base = str(model)[:-len(".json")]
        h = json.loads(Path(base + ".drsums.json").read_text())
        self.h, self.NP, self.NT, self.ORD, self.NC, self.NA = h, h["NP"], h["NT"], h["ORD"], h["NCAND"], h["NA"]
        self.cells, self.kinds, self.F = self.NP * self.NT * self.ORD, h["kinds"], h["folds"]
        nk = h["NOPP"] + 1
        raw = np.fromfile(base + ".drsums.bin", dtype=np.float64).reshape(self.F, (1 + nk) * self.cells * self.NC * 3)
        self.s0 = raw[:, :self.cells * self.NC * 3].reshape(self.F, self.cells, self.NC, 3)
        self.sk = raw[:, self.cells * self.NC * 3:].reshape(self.F, nk, self.cells, self.NC, 3)
        self.rows = float(sum(h["rows"]))
        self.rows_kind = self.sk[:, :, :, self.NA, 2].sum(axis=(0, 2))  # every decision has the current logic as a candidate
        c = np.arange(self.cells)
        self.k, self.t, self.p = c % self.ORD, (c // self.ORD) % self.NT, c // (self.ORD * self.NT)
        self.groups = {"cell": c, "tb": self.t * 5 + np.vectorize(KC)(self.k), "tk": self.t * self.ORD + self.k, "t": self.t}
        self.maps = None
        if Path(base + ".mapsums.json").is_file():
            m = json.loads(Path(base + ".mapsums.json").read_text())
            self.parts, self.NB = m["parts"], m["NB"]
            self.maps = np.memmap(base + ".mapsums.bin", dtype=np.float64, mode="r",
                                  shape=(self.F, self.cells, len(self.parts), self.NB, self.NC, 3))


def stats(S):
    """mean and se of D per (..., candidate) from (sum, sum of squares, n)."""
    n = S[..., 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.where(n > 0, S[..., 0] / n, 0.0)
        se = np.where(n > 1, np.sqrt(np.maximum(0.0, S[..., 1] / n - m * m) / n), np.inf)
    return m, se, n


def pool(S, group):
    """Sums per cell replaced by its group's (S: [cells, cand, 3])."""
    out = np.zeros((group.max() + 1,) + S.shape[1:])
    np.add.at(out, group, S)
    return out[group]


def pick(m, se, n, z, min_n=30):
    """Per cell the candidate maximising m - z se where positive (and n >= min_n), else -1."""
    score = np.where(n >= min_n, m - z * se, -np.inf)
    best = score.argmax(axis=-1)
    return np.where(np.take_along_axis(score, best[..., None], -1)[..., 0] > 0, best, -1)


def rule_static(X, S, name):
    """The selection (candidate per cell, -1 the base) of a static rule on sums S [cells, cand, 3]."""
    if "+" in name:
        a, b = name.split("+")
        sel, own = rule_static(X, S, a), rule_static(X, S, b)
        return np.where(own >= 0, own, sel)
    m = re.fullmatch(r"(cell|tb|tk|t)-z([\d.]+)", name)
    if m:
        return pick(*stats(pool(S, X.groups[m.group(1)])), float(m.group(2)))
    m = re.fullmatch(r"hier-z([\d.]+)-t([\d.]+)", name)
    if m:
        z, tau = float(m.group(1)), float(m.group(2)) / 100
        mc, sc, n = stats(S)
        mg, sg, _ = stats(pool(S, X.groups["tb"]) - S)  # the rest of the group
        w1, w2 = 1 / np.maximum(sc, 1e-9) ** 2, 1 / (np.minimum(sg, 1e6) ** 2 + tau * tau)
        w1 = np.where(np.isfinite(sc), w1, 0.0)
        post, sd = (w1 * mc + w2 * mg) / (w1 + w2), 1 / np.sqrt(w1 + w2)
        return pick(post, sd, np.where(n > 0, 1e9, 0), z)
    raise SystemExit(f"unknown rule {name}")


def split_sums(X, fold_mask, part, cut):
    """[2 sides][cells, cand, 3] of the folds in fold_mask, for partition `part` cut at bin `cut`."""
    M = X.maps[fold_mask].sum(axis=0)[:, part]  # cells, bins, cand, 3
    return np.stack([M[:, :cut].sum(axis=1), M[:, cut:].sum(axis=1)])


def rule_map(X, sides, name):
    """A map-keyed rule's selection per side from sides [2][cells, cand, 3]."""
    m = re.fullmatch(r"~s([\d.]+):tb-z([\d.]+)", name)
    if m:
        s, z = float(m.group(1)) / 100, float(m.group(2))
        both = pool(sides[0] + sides[1], X.groups["tb"])
        out = []
        for i in (0, 1):
            ms, ss, n = stats(pool(sides[i], X.groups["tb"]))
            mo, so, _ = stats(pool(sides[1 - i], X.groups["tb"]))
            w1, w2 = np.where(np.isfinite(ss), 1 / np.maximum(ss, 1e-9) ** 2, 0.0), np.where(np.isfinite(so), 1 / (so ** 2 + s * s), 0.0)
            post, sd = (w1 * ms + w2 * mo) / np.maximum(w1 + w2, 1e-12), 1 / np.sqrt(np.maximum(w1 + w2, 1e-12))
            out.append(pick(post, sd, np.where(stats(both)[2] > 0, 1e9, 0), z))
        return out
    return [rule_static(X, sides[i], name.lstrip(":")) for i in (0, 1)]


def score(S, sel):
    """(gain sum, variance sum, decisions moved) of a selection on sums S [cells, cand, 3]."""
    c = np.nonzero(sel >= 0)[0]
    x = S[c, sel[c]]
    n = np.maximum(x[:, 2], 1)
    return x[:, 0].sum(), (x[:, 1] - x[:, 0] ** 2 / n).sum(), x[:, 2].sum()


def evaluate(X, name):
    """Cross-fitted: per fold, the selection on the other folds scored on it. Returns per-decision gain, se, the
    share of decisions moved, and the gain per opponent kind (points)."""
    g = v = moved = 0.0
    gk, vk = np.zeros(len(X.rows_kind)), np.zeros(len(X.rows_kind))
    mk = re.fullmatch(r"(\w+)@(\d)(.*)", name)
    per_fold = []
    for f in range(X.F):
        g0 = g
        others = np.arange(X.F) != f
        if mk:
            part = [p["name"] for p in X.parts].index(mk.group(1))
            sels = rule_map(X, split_sums(X, others, part, int(mk.group(2))), mk.group(3))
            held = split_sums(X, np.arange(X.F) == f, part, int(mk.group(2)))
            for i in (0, 1):
                a, b, c = score(held[i], sels[i])
                g, v, moved = g + a, v + b, moved + c
        else:
            sel = rule_static(X, X.s0[others].sum(axis=0), name)
            a, b, c = score(X.s0[f], sel)
            g, v, moved = g + a, v + b, moved + c
            for q in range(len(gk)):
                a, b, _ = score(X.sk[f, q], sel)
                gk[q] += a
                vk[q] += b
        per_fold.append((g - g0) / max(1.0, X.s0[f, :, X.NA, 2].sum()))
    # The folds are disjoint sets of maps, so their spread is an honest error: the formula's se takes a team's ~30
    # decisions as independent, though they share one game's outcome.
    X.fold_se = 100 * float(np.std(per_fold, ddof=1)) / np.sqrt(len(per_fold))
    kinds = None if mk else [(100 * gk[q] / max(1, X.rows_kind[q]), 100 * np.sqrt(vk[q]) / max(1, X.rows_kind[q])) for q in range(len(gk))]
    return 100 * g / X.rows, 100 * np.sqrt(v) / X.rows, moved / X.rows, kinds


def selection(X, name):
    """The rule on all folds, as candidate.py cells: [{picks, type, k, arm, gain, n}] (map rules: per side)."""
    types, mk = X.h["types"], re.fullmatch(r"(\w+)@(\d)(.*)", name)

    def cells(S, sel):
        m, _, n = stats(S)
        return [{"picks": int(X.p[c]) + 3, "type": types[X.t[c]], "k": int(X.k[c]), "current_family": None,
                 "arm": -1 if sel[c] == X.NA else int(sel[c]), "gain": float(m[c, sel[c]]), "n": float(n[c, sel[c]])}
                for c in np.nonzero(sel >= 0)[0]]
    if not mk:
        S = X.s0.sum(axis=0)
        return cells(S, rule_static(X, S, name))
    part = [p["name"] for p in X.parts].index(mk.group(1))
    sides = split_sums(X, np.ones(X.F, bool), part, int(mk.group(2)))
    sels = rule_map(X, sides, mk.group(3))
    return {"feature": mk.group(1), "bin": int(mk.group(2)), "threshold_z": X.parts[part]["cuts"][int(mk.group(2)) - 1],
            "low": cells(sides[0], sels[0]), "high": cells(sides[1], sels[1])}


STATIC = ["cell-z2", "cell-z2.5", "cell-z3", "tk-z2", "tk-z3", "tb-z2", "tb-z2.5", "tb-z3", "t-z2", "t-z3", "hier-z2-t50", "hier-z3-t50",
          "hier-z2-t25", "hier-z2-t100", "tb-z2+cell-z3", "tb-z3+cell-z3", "tb-z2.5+cell-z3.5"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    ap.add_argument("--rules", help="comma-separated (default: a standard list)")
    ap.add_argument("--maps", action="store_true")
    ap.add_argument("--plus", action="append", default=[], help="another model's sums, added to MODEL's (the same folds: e.g. two halves of a lab fitted apart)")
    ap.add_argument("--kmax", type=int, help="only ordinals below this (a sparse lab forces the first few)")
    ap.add_argument("--on", help="another model's sums (later, independent games): each rule's selection on all of MODEL's folds, scored there")
    ap.add_argument("--write")
    ap.add_argument("--out")
    a = ap.parse_args()
    X = Sums(a.model)
    for other in a.plus:
        Y = Sums(other)
        X.s0, X.sk, X.rows, X.rows_kind = X.s0 + Y.s0, X.sk + Y.sk, X.rows + Y.rows, X.rows_kind + Y.rows_kind
    if a.kmax is not None:
        # Candidates at later ordinals are never selected: their sums are emptied (the decisions still count in rows).
        late = X.k >= a.kmax
        X.s0, X.sk = X.s0.copy(), X.sk.copy()
        X.s0[:, late, :X.NA, :] = 0
        X.sk[:, :, late, :X.NA, :] = 0
    if a.write:
        out = {a.write: selection(X, a.write)}
        Path(a.out).write_text(json.dumps(out) + "\n")
        n = len(out[a.write]) if isinstance(out[a.write], list) else (len(out[a.write]["low"]), len(out[a.write]["high"]))
        print(f"{a.out}: {a.write}, {n} cells")
        return
    rules = a.rules.split(",") if a.rules else list(STATIC)
    if a.maps and not a.rules:
        for p in X.parts:
            for b in (2, 4, 6):
                rules += [f"{p['name']}@{b}:tb-z2", f"{p['name']}@{b}:tb-z3", f"{p['name']}@{b}~s50:tb-z2", f"{p['name']}@{b}:cell-z2"]
    print(f"{X.rows:.0f} decisions; per kind {dict(zip(X.kinds, X.rows_kind.astype(int)))}")
    if a.on:
        # Replication: nothing of the scoring games went into the selection, the outcome model or the proposal's steer.
        Y = Sums(a.on)
        print(f"selections of {a.model} scored on {a.on} ({Y.rows:.0f} decisions)")
        for r in rules:
            sel = rule_static(X, X.s0.sum(axis=0), r)
            g, v, moved = score(Y.s0.sum(axis=0), sel)
            kinds = [score(Y.sk[:, q].sum(axis=0), sel) for q in range(len(Y.rows_kind))]
            print(f"{r:28s} {100 * g / Y.rows:+.3f} ± {100 * np.sqrt(v) / Y.rows:.3f}  moves {100 * moved / Y.rows:3.0f}%  | " +
                  ", ".join(f"{k} {100 * x[0] / max(1, n):+.3f}±{100 * np.sqrt(x[1]) / max(1, n):.3f}" for k, x, n in zip(Y.kinds, kinds, Y.rows_kind) if n > 0))
        return
    for r in rules:
        g, se, moved, kinds = evaluate(X, r)
        tail = "" if kinds is None else "  | " + ", ".join(f"{k} {x:+.3f}±{s:.3f}" for k, (x, s) in zip(X.kinds, kinds) if X.rows_kind[X.kinds.index(k)] > 0)
        print(f"{r:28s} {g:+.3f} ± {se:.3f} (folds ±{X.fold_se:.3f})  moves {100 * moved:3.0f}%{tail}")


if __name__ == "__main__":
    main()
