#!/usr/bin/env python3
"""cooked_ab.py BATCH ANA [E_MIN GAP]: in an A/B batch (bot 1 = CAND), comeback rate of each bot once cooked
(the other side's tributed >= E_MIN and ahead by >= GAP), and per map kind. Extract BATCH into ANA first."""
import json, gzip, os, sys, collections
B, ANA = sys.argv[1], sys.argv[2]
E_MIN, GAP = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (600, 200)
ix = json.load(open(f'{ANA}/index.json'))
src = {os.path.basename(g['source']): g['dir'] for g in ix['games']}
c = collections.Counter()
for f in sorted(os.listdir(B)):
    if not f.endswith('.repl26a') or f not in src: continue
    d = src[f]; cand = 0 if f[-10:-8] == '12' else 1
    m = json.load(open(f'{ANA}/{d}/meta.json'))
    mp = json.load(open(f"{ANA}/maps/{m['map']['hash']}.json"))
    kind = 'one' if len(mp['altars']) == 1 else 'multi'
    R = json.load(gzip.open(f'{ANA}/{d}/rounds.json.gz'))
    w = m['result']['winner']
    for i in range(len(R['round'])):
        hit = None
        for t in (0, 1):
            if R['gems'][1 - t][i] >= E_MIN and R['gems'][1 - t][i] - R['gems'][t][i] >= GAP: hit = t
        if hit is not None:
            who = 'cand' if hit == cand else 'ref'
            for k in (kind, 'all'):
                c[(k, who, 'cooked')] += 1; c[(k, who, 'won')] += w == hit
            break
for k in ('one', 'multi', 'all'):
    for who in ('cand', 'ref'):
        n = c[(k, who, 'cooked')]
        if n: print(k, who, f'cooked {n} comeback {c[(k, who, "won")]} = {100 * c[(k, who, "won")] / n:.1f}%')
