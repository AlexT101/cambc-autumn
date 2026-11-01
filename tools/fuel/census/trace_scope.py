"""Per map: the fuel from entering a scope to the next traced event (or the run-out), on traced OOF turns.

    py tools/fuel/census/trace_scope.py replays/fuel/cen min_camp_damage
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from trace import lines, parse_ctr  # noqa: E402

root, scope = sys.argv[1], sys.argv[2]
per = defaultdict(list)
for z, name, ln in lines(root):
    if not ln.startswith("CTR "):
        continue
    rnd, champ, ev = parse_ctr(ln)
    tail = ev + [("o", "OOF", 0, 0, 0)]
    for a, b in zip(tail, tail[1:]):
        if a[0] == "e" and a[1] == scope:
            per[z.parent.name.rsplit("-", 1)[0]].append((a[3] - b[3], b[1] == "OOF", a[3]))
tot = sum(len(v) for v in per.values())
print(f"{scope}: {tot} entries on traced OOF turns")
for m, v in sorted(per.items(), key=lambda kv: -sum(x[0] for x in kv[1])):
    c = sorted(x[0] for x in v)
    oof = [x for x in v if x[1]]
    print(f"  {m:34s} n {len(v):5d} mean {sum(c)//len(c):6d} p50 {c[len(c)//2]:6d} max {c[-1]:6d}  ran out inside {len(oof):4d}"
          f" (entered with {sum(x[2] for x in oof)//max(1,len(oof)):6d})")
