"""The lab's estimate (dumped sums of dfit.mjs --dr) of pre-stated, pooled edits to the shipped table: family F,
in each type's usual stat, as every champion's k-th new emblem where the table has no F by then (collectors.py
builds the bot). One changed cell a champion, so the lab's single-decision estimand is the policy's.
    py pooled_edits.py MODEL.json TABLE.h LAB_TEAM_GAMES [--ab]     # --ab: the 19 edits A/B'd in round 4, side by side"""
import collections, importlib.util, re, sys
from pathlib import Path
import numpy as np
spec = importlib.util.spec_from_file_location('sel', Path(__file__).resolve().parents[3] / 'tools/emblab/select.py')
sel = importlib.util.module_from_spec(spec); spec.loader.exec_module(sel)
X = sel.Sums(sys.argv[1]); teams = float(sys.argv[3])
rows = [list(map(int, m.group(1).split(', '))) for m in re.finditer(r"\{([\d, ]+)\}, // \w+", Path(sys.argv[2]).read_text())]
F = ["monster","power","durability","treasure","jungle","home","bruiser","tribute","capture","prospector","hunter","skirmish","greed","collectors"]
main = {}
for t in range(13):
    c = collections.Counter(x % 3 for q in range(3) for x in rows[q * 13 + t][3:] if x != 255)
    main[t] = c.most_common(1)[0][0] if c else 0
S = X.s0.sum(axis=0)
def insert(f, k):
    g = v = 0.0
    for p in range(3):
        for t in range(13):
            if any(x != 255 and x // 3 == f for x in rows[p * 13 + t][:k + 1]): continue
            x = S[(p * 13 + t) * 12 + k, f * 3 + main[t]]
            g += x[0]; v += x[1] - x[0] ** 2 / max(x[2], 1)
    return 100 * g / teams, 100 * np.sqrt(v) / teams
AB = {('collectors',1):-1.3,('collectors',2):-0.6,('collectors',3):-0.2,('collectors',4):0.2,('collectors',6):-0.1,('collectors',8):0.4,
      ('skirmish',4):0.55,('durability',4):0.1,('monster',4):0.1,('prospector',4):0.1,('jungle',4):0.0,('capture',4):-0.2,('treasure',4):-0.3,
      ('hunter',4):-0.3,('home',4):-0.3,('tribute',4):-0.9,('skirmish',3):0.1,('skirmish',5):0.3,('skirmish',6):0.5}
if '--ab' in sys.argv:
    xs, ys = [], []
    for (fam, k), w in AB.items():
        g, se = insert(F.index(fam), k); xs.append(g); ys.append(w)
        print(f"  {fam:11s} k{k}   lab {g:+.2f} ± {se:.2f}   A/B {w:+.2f}")
    xs, ys = np.array(xs), np.array(ys)
    print(f"correlation {np.corrcoef(xs, ys)[0, 1]:+.2f}; mean lab {xs.mean():+.2f}, A/B {ys.mean():+.2f}; rms gap {np.sqrt(((xs - ys) ** 2).mean()):.2f}")
else:
    out = sorted(((*insert(f, k), F[f], k) for f in range(14) if F[f] != 'greed' for k in range(12)), key=lambda r: -r[0] / max(r[1], 1e-9))
    for g, se, fam, k in out[:12] + out[-6:]:
        print(f"  {fam:11s} k{k:<2d}  {g:+.2f} ± {se:.2f} points a team  (z {g / se:+.1f})" + (f"   A/B {AB[(fam, k)]:+.2f}" if (fam, k) in AB else ""))
