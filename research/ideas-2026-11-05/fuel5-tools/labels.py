"""Per-label inclusive/self fuel from census CEN lines, over turns of a group (oof-first, oof, heavy) that have a component.

    python3 research/ideas-2026-11-05/fuel5-tools/labels.py GAMES_DIR [--group oof|first|heavy|all] [--with strike_search] [--prefix ss.]
"""
import argparse, collections, statistics, sys
sys.path.insert(0, "tools/fuel/census")
import census

ap = argparse.ArgumentParser()
ap.add_argument("dirs", nargs="+")
ap.add_argument("--group", default="first")
ap.add_argument("--with", dest="with_", default=None)
ap.add_argument("--prefix", default="")
ap.add_argument("--top", type=int, default=40)
a = ap.parse_args()
rows = census.load(a.dirs)
def grp(r):
    if r["oof"] and not r["late"]: return "first"
    if r["oof"]: return "late"
    return "heavy"
sel = [r for r in rows if a.group == "all" or grp(r) == a.group or (a.group == "oof" and r["oof"])]
if a.with_: sel = [r for r in sel if census.inc(r, a.with_) >= 1000]
print(f"turns {len(sel)} (of {len(rows)})")
inc, slf, calls, present = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
for r in sel:
    for k, (i, s, c) in r["c"].items():
        if not k.startswith(a.prefix): continue
        inc[k] += i; slf[k] += s; calls[k] += c; present[k] += 1
n = max(1, len(sel))
print(f"  {'label':24s} {'present':>8s} {'incl/turn':>10s} {'self/turn':>10s} {'incl/call':>10s} {'calls/turn':>10s}")
for k, v in inc.most_common(a.top):
    print(f"  {k:24s} {present[k]/n:8.0%} {v/n:10.0f} {slf[k]/n:10.0f} {v/max(1,calls[k]):10.0f} {calls[k]/n:10.2f}")
