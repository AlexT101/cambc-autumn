"""Rank pre-stated pooled edits to a table with the dense lab's sums: one changed cell a champion.
    py rank_edits.py TABLE.h [--top 25]
Edits: family F in stat S (main: the type's usual one; or str/foc/hp for everyone) as every type's k-th emblem where
the table has no F at or before k; and column k back to the current logic. Per edit: the lab's points a team over all
lab teams (dmodel-dense), and over the teams of ocean's own draft only (dmodel-src, source "model": thinner)."""
import collections, importlib.util, re, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('sel', ROOT / 'tools/emblab/select.py')
sel = importlib.util.module_from_spec(spec); spec.loader.exec_module(sel)
F = ["monster","power","durability","treasure","jungle","home","bruiser","tribute","capture","prospector","hunter","skirmish","greed","collectors"]
ST = ["str", "foc", "hp"]
X = sel.Sums(str(ROOT / 'replays/emblab/r4/dmodel-dense.json'))
Y = sel.Sums(str(ROOT / 'replays/emblab/r4/dmodel-src.json'))
S_all, teams_all = X.s0.sum(axis=0), 1791740.0
qm = Y.kinds.index('model')
S_mod = Y.sk[:, qm].sum(axis=0)
teams_mod = teams_all * Y.rows_kind[qm] / Y.rows_kind.sum() * 0.93   # model teams log ~7% more decisions a team than the average
rows = [list(map(int, m.group(1).split(', '))) for m in re.finditer(r"\{([\d, ]+)\}, // \w+", Path(sys.argv[1]).read_text())]
main = {}
for t in range(13):
    c = collections.Counter(x % 3 for q in range(3) for x in rows[q * 13 + t][3:] if x != 255)
    main[t] = c.most_common(1)[0][0] if c else 0

def cells(f, k, stat):
    """(cell, candidate) per row of an edit; stat: 'main' or 0..2; f < 0: the column to the current logic."""
    out = []
    for p in range(3):
        for t in range(13):
            r = rows[p * 13 + t]
            if f < 0:
                if r[k] != 255: out.append(((p * 13 + t) * 12 + k, X.NA))
            elif not any(x != 255 and x // 3 == f for x in r[:k + 1]):
                out.append(((p * 13 + t) * 12 + k, f * 3 + (main[t] if stat == 'main' else stat)))
    return out

def est(S, teams, cs):
    g = v = 0.0
    for c, a in cs:
        x = S[c, a]; g += x[0]; v += x[1] - x[0] ** 2 / max(x[2], 1)
    return 100 * g / teams, 100 * np.sqrt(v) / teams

if __name__ == '__main__':
    top = int(sys.argv[sys.argv.index('--top') + 1]) if '--top' in sys.argv else 25
    out = []
    for k in range(12):
        out.append((f"column k{k} -> current logic", est(S_all, teams_all, cells(-1, k, 0)), est(S_mod, teams_mod, cells(-1, k, 0))))
        for f in range(14):
            if F[f] == 'greed': continue
            for stat in ('main', 0, 1, 2):
                cs = cells(f, k, stat)
                if cs: out.append((f"{F[f]}-{stat if stat == 'main' else ST[stat]} at k{k}", est(S_all, teams_all, cs), est(S_mod, teams_mod, cs)))
    out.sort(key=lambda r: -r[1][0] / max(r[1][1], 1e-9))
    print(f"{len(out)} edits; lab points a team: all lab teams | ocean's own draft's teams")
    for name, a, m in out[:top]:
        print(f"  {name:32s} {a[0]:+.2f} ± {a[1]:.2f} (z {a[0] / a[1]:+.1f}) | {m[0]:+.2f} ± {m[1]:.2f}")
