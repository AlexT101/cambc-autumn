#!/usr/bin/env python3
"""pair.py BASE_RESULTS AB_NAME...: each A/B's win rate paired with the one-side self-play baseline on the same maps
(the mirror's game on a map is the same from either side, so it gives the base outcome for both). Per map: CAND's
mean minus the base's (0.5 for every map, as the mirror splits a map's two sides). Mean, SE over maps, flips."""
import json, sys, glob, os, math

def a_won(results):
    out = {}
    for m in json.load(open(results))['matches']:
        if m.get('winner') is None: continue
        out[os.path.basename(m['map'])] = m['winner'] == m['order'][0]
    return out

base = a_won(sys.argv[1])
for name in sys.argv[2:]:
    per = {}
    flips = n = 0
    for b in sorted(glob.glob(f'replays/batch-*-ab-{name}-*')) + ([name] if os.path.isdir(name) else []):
        for m in json.load(open(f'{b}/results.json'))['matches']:
            mp = os.path.basename(m['map'])
            if m.get('winner') is None or mp not in base: continue
            cand_a = m['order'][0] == 0
            won = m['winner'] == 0
            bw = base[mp] if cand_a else not base[mp]
            per.setdefault(mp, []).append(won - bw)
            flips += won != bw; n += 1
    full = [sum(v) / 2 for v in per.values() if len(v) == 2]
    if not full: print(name, 'no pairs'); continue
    mu = sum(full) / len(full)
    sd = math.sqrt(sum((x - mu) ** 2 for x in full) / max(1, len(full) - 1))
    print(f'{name}: games {n}, maps {len(full)}, flips {100 * flips / n:.1f}%, paired diff {100 * mu:+.2f} ± {196 * sd / math.sqrt(len(full)):.2f} (win {50 + 100 * mu:.2f}%)')
