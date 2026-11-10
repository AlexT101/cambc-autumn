"""heavy.py BASE.json CAND.json: on identical 100M games, per-turn fuel saving overall and on base turns >= 70k/85k/95k, and the count of turns over 100k / 95k."""
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
A = {(g['map'], g['side']): g for g in a['games']}; B = {(g['map'], g['side']): g for g in b['games']}
S = {k: [0, 0, 0] for k in ('all', '>=70k', '>=85k', '>=95k', '>=100k')}; lo = {'all': 0, '>=70k': 70000, '>=85k': 85000, '>=95k': 95000, '>=100k': 100000}
over = [0, 0]; over95 = [0, 0]; games = 0
for k in A:
    if k not in B or A[k]['replay'] != B[k]['replay']: continue
    games += 1
    for x, y in zip(A[k]['play'], B[k]['play']):
        over[0] += x > 100000; over[1] += y > 100000; over95[0] += x > 95000; over95[1] += y > 95000
        for n in S:
            if x >= lo[n]: S[n][0] += 1; S[n][1] += x - y; S[n][2] += x
print(f'{games} identical games; turns over 100k {over[0]} -> {over[1]} ({100*(over[1]/over[0]-1):+.1f}%); over 95k {over95[0]} -> {over95[1]} ({100*(over95[1]/over95[0]-1):+.1f}%)')
for n, (c, s, t) in S.items(): print(f'  {n:7s} turns {c:7d}  saving {s/max(1,c):7.0f}/turn  {100*s/max(1,t):5.2f}%')
