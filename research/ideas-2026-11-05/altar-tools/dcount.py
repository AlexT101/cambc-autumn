#!/usr/bin/env python3
"""dcount.py BATCH: per game, bot-1's D-line decision counts (U guard, E stop_ender, W wait_altar, C chase) and result."""
import json, sys, zipfile, glob, os, collections, re
b = sys.argv[1]
res = json.load(open(f'{b}/results.json'))
tot = collections.Counter()
for f in sorted(glob.glob(f'{b}/*.repl26a')):
    side = f[-10:-8]  # 12: bot1 is team A
    team = 'a' if side == '12' else 'b'
    z = zipfile.ZipFile(f)
    c = collections.Counter(); first = None
    for line in z.read(f'team-{team}.stdout').decode(errors='replace').splitlines():
        if line.startswith('D '):
            p = line.split()
            c[p[3]] += 1
            if p[3] == 'U' and first is None: first = int(p[1])
    for k in 'UEWC': tot[k] += c[k]
    tot['games_U'] += c['U'] > 0
    if len(sys.argv) > 2: print(os.path.basename(f), {k: c[k] for k in 'UEWC'}, 'firstU', first)
print(dict(tot), 'games', len(glob.glob(f'{b}/*.repl26a')))
