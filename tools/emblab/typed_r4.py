"""Emblem lab round 5: the typed edits. For each of the most drafted types, one arm at one ordinal of its rows (all
pick counts), where the row has no such family by then: the 12 that round 4's per-decision sums rank highest (z of
the summed doubly robust gain, replays/emblab/r4/dmodel-dense) and 6 drawn at random as controls, which test
whether that ranking is worth anything. Ordinal 4 (Skirmish, CHANGES 499, after round 4) is left alone."""
import importlib.util
from pathlib import Path

import numpy as np

import edits as ed

ROOT = Path(__file__).resolve().parents[2]
TYPED = ["cassi", "issac", "prism", "vesper_vale", "heart_of_ruin", "willow", "marcella"]
RANKED, CONTROLS, PER_K = 12, 6, 3


def add_edits(add, table, main, rng, family_at):
    spec = importlib.util.spec_from_file_location("sel", ROOT / "tools/emblab/select.py")
    sel = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sel)
    X = sel.Sums(str(ROOT / "replays/emblab/r4/dmodel-dense.json"))
    S = X.s0.sum(axis=0)
    for name in TYPED:
        t = ed.TYPES.index(name)
        cands = []
        for f in range(14):
            if ed.FAMILIES[f] == "greed":
                continue
            for k in range(12):
                if k == 4:
                    continue
                for stat in range(3):
                    cells = family_at(table, main, ed.FAMILIES[f], k, "ow", stat=stat, types={t})
                    if not cells:
                        continue
                    g = v = 0.0
                    for p, _, kk, a in cells:
                        x = S[(p * 13 + t) * 12 + kk, a]
                        g += x[0]
                        v += x[1] - x[0] ** 2 / max(x[2], 1)
                    cands.append((g / np.sqrt(v) if v > 0 else 0.0, f, k, stat, cells))
        cands.sort(key=lambda c: -c[0])
        taken, per_k = [], {}
        for c in cands:
            if len(taken) == RANKED:
                break
            if per_k.get(c[2], 0) < PER_K:
                per_k[c[2]] = per_k.get(c[2], 0) + 1
                taken.append(c)
        rest = [c for c in cands if c not in taken and c[3] == main[t]]
        for tier, group in (("typed", taken), ("typed-ctl", rng.sample(rest, CONTROLS))):
            for z, f, k, stat, cells in group:
                add(f"{name}-{ed.FAMILIES[f]}-{ed.STATS[stat]}-k{k}", tier, cells, need=ed.pick_of(t))
