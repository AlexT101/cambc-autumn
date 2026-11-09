"""A priori table: per situation predicate, every action class's mean gain over ocean's own action (no discovery
step), on all forks, with each half's mean and a 95% bootstrap CI over games.

    py tools/combatlab/fork_branch_table.py ROWS.jsonl [ROWS2...] --preds br=R,br=C,br=A [--mark 30] [--key CL] [--min-n 40]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fork_patterns as fp  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rows", nargs="+")
    ap.add_argument("--preds", default="br=R,br=C,br=A")
    ap.add_argument("--mark", default="30")
    ap.add_argument("--key", default="CL")
    ap.add_argument("--min-n", type=int, default=40)
    a = ap.parse_args()
    rows = [r for f in a.rows for r in fp.load(f)]
    want = a.preds.split(",")
    tab = fp.table(rows, a.mark, a.key)
    nf = {p: sum(1 for r in rows if p in fp.preds(r)) for p in want}
    for p in want:
        print(f"\n== {p}: {nf[p]} forks (mark {a.mark}, {a.key})")
        out = []
        for (pp, c), items in tab.items():
            if pp != p or len(items) < a.min_n:
                continue
            m, lo, hi = fp.cluster_ci(items)
            h = [[v for g, v in items if any(r["src"] + "|" + r["game"] == g for r in [])] for _ in range(0)]
            h0 = [v for g, v in items if fp.half_game(g) == 0]
            h1 = [v for g, v in items if fp.half_game(g) == 1]
            out.append((m, c, len(items), lo, hi, sum(h0) / max(1, len(h0)), sum(h1) / max(1, len(h1))))
        for m, c, n, lo, hi, a0, a1 in sorted(out, reverse=True):
            flag = " *" if lo > 0 else " -" if hi < 0 else ""
            print(f"  {c:28s} n {n:5d}  {m:+.3f} [{lo:+.3f},{hi:+.3f}]  halves {a0:+.3f} {a1:+.3f}{flag}")


if __name__ == "__main__":
    main()
