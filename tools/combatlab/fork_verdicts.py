"""Verdict-arm gains (forkgame `home:V:N` / `chase:V:N` arms) by situation, per map-hash half and per rows file:
the a priori class gain of fork_patterns.gains (mean over reps, forks where the forced verdict is ocean's own left
out) with a 95% bootstrap CI over games; `*` / `-` mark a CI above / below zero.

    py tools/combatlab/fork_verdicts.py ROWS.jsonl [ROWS2...] [--marks 10,30] [--keys KD,CL,E]
        [--classes chase=1x3,chase=1x8,home=0x3,home=0x8,home=1x3,chase=0x3]
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fork_patterns import cluster_ci, gains  # noqa: E402


def not_rc(s):
    return s["branch"] not in ("R", "C")


PREDS = [
    ("all", lambda s: True),
    ("br=F", lambda s: s["branch"] == "F"),
    ("br=B", lambda s: s["branch"] == "B"),
    ("br=R", lambda s: s["branch"] == "R"),
    ("br=C", lambda s: s["branch"] == "C"),
    ("notRC", not_rc),
    ("notRC&tgt_hp>=.45", lambda s: not_rc(s) and s["near_hp"] is not None and s["near_hp"] >= .45),
    ("notRC&tgt_hp<.45", lambda s: not_rc(s) and s["near_hp"] is not None and s["near_hp"] < .45),
    ("notRC&tgt_near_its_home<=8", lambda s: not_rc(s) and s["near_home"] is not None and s["near_home"] <= 8),
    ("notRC&tgt_far_its_home>8", lambda s: not_rc(s) and s["near_home"] is not None and s["near_home"] > 8),
    ("notRC&tgt_bag>=20", lambda s: not_rc(s) and (s["near_gems"] or 0) >= 20),
    ("notRC&a8>=e8", lambda s: not_rc(s) and s["a8"] >= s["e8"]),
    ("notRC&a8<e8", lambda s: not_rc(s) and s["a8"] < s["e8"]),
    ("notRC&hp>=.5", lambda s: not_rc(s) and s["hp"] >= .5),
    ("notRC&hp<.5", lambda s: not_rc(s) and s["hp"] < .5),
    ("notRC&d<=4", lambda s: not_rc(s) and s["d_enemy"] <= 4),
    ("notRC&d5-8", lambda s: not_rc(s) and 5 <= s["d_enemy"] <= 8),
    ("notRC&home16+", lambda s: not_rc(s) and s["home"] >= 16),
    ("R&e8>0", lambda s: s["branch"] == "R" and s["e8"] > 0),
    ("R&e8>0&hp>=.5", lambda s: s["branch"] == "R" and s["e8"] > 0 and s["hp"] >= .5),
    ("R&e8>0&hp<.5", lambda s: s["branch"] == "R" and s["e8"] > 0 and s["hp"] < .5),
    ("R&e8=0", lambda s: s["branch"] == "R" and s["e8"] == 0),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rows", nargs="+")
    ap.add_argument("--marks", default="10,30")
    ap.add_argument("--keys", default="KD,CL,E")
    ap.add_argument("--classes", default="chase=1x3,chase=1x8,home=0x3,home=0x8,home=1x3,chase=0x3")
    a = ap.parse_args()
    rows = {f: [json.loads(l) for l in open(f)] for f in a.rows}
    for m in a.marks.split(","):
        for key in a.keys.split(","):
            print(f"\n== mark {m} {key}")
            print(f"{'pred':30s} {'cls':10s}" + "".join(f" {os.path.basename(f)[:6] + ' h' + str(h):>27s}" for f in a.rows for h in (0, 1)))
            for cls in a.classes.split(","):
                for pn, fn in PREDS:
                    line, seen = f"{pn:30s} {cls:10s}", False
                    for f in a.rows:
                        for h in (0, 1):
                            it = []
                            for r in rows[f]:
                                if r["half"] != h or not fn(r["sit"]):
                                    continue
                                g = gains(r, m, key)
                                if g and cls in g:
                                    it.append((r["game"], g[cls]))
                            mean, lo, hi = cluster_ci(it)
                            if mean is None:
                                line += f" {'-':>27s}"
                                continue
                            seen = True
                            sig = "*" if lo > 0 else "-" if hi < 0 else " "
                            line += f" {len(it):4d} {mean:+.3f}[{lo:+.3f},{hi:+.3f}]{sig}"
                    if seen:
                        print(line)


if __name__ == "__main__":
    main()
