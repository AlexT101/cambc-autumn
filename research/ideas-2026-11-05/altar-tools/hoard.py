#!/usr/bin/env python3
"""hoard.py ANA: teams holding a winning bag (tributed + one body's bag >= 1000) for 30+ rounds; how the game ended."""
import json, gzip, os, sys, collections
ANA = sys.argv[1]
c = collections.Counter(); size = []
for d in os.listdir(ANA):
    if not os.path.exists(f'{ANA}/{d}/meta.json'): continue
    m = json.load(open(f'{ANA}/{d}/meta.json'))
    R = json.load(gzip.open(f'{ANA}/{d}/rounds.json.gz'))
    w = m['result']['winner']; c['games'] += 1
    for t in (0, 1):
        held = 0; mx = 0
        for i in range(len(R['round'])):
            best = max((ch['gems'][i] or 0) for ch in R['champions'] if ch['team'] == t)
            if R['gems'][t][i] + best >= 1000: held += 1; mx = max(mx, best)
        if held >= 30:
            c['team_held30'] += 1; c['held30_lost'] += w != t; c['held_rounds'] += held; size.append(mx)
print(dict(c)); size.sort(); print('bag sizes q', [size[int(len(size) * q)] for q in (0.1, 0.5, 0.9)] if size else None)
