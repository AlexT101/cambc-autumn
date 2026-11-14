"""Early economy, Fish side vs ours: by r100/r200, capture count and gold, kill gold, first capture round, clears,
and gold by champion."""
import sys, os, collections
sys.path.insert(0, '/home/ubuntu/tmp-offload/fishre/tools')
from fl import games, US
SINCE = '2026-11-08T16'
filt = None if os.environ.get('LOCAL') else (lambda g: g['opp'] == US and g['created'] >= SINCE)
A = collections.defaultdict(list); P = collections.defaultdict(list)
for g in games(filt):
    F = g['fish']; ch = g['rd']['champions']; team = {c['id']: c['team'] for c in g['meta']['champions']}
    nm = {c['id']: c['name'] for c in g['meta']['champions']}
    for R in (100, 200):
        for t in (0, 1):
            s = 'F' if t == F else 'O'
            caps = [e for e in g['ev'] if e['k'] == 'capture' and e['r'] <= R and e.get('team') == t]
            A[(s, R, 'captures')].append(len(caps))
            A[(s, R, 'capgold')].append(sum(sh[2] for e in caps for sh in e['shares']))
            A[(s, R, 'capgems')].append(sum(sh[1] for e in caps for sh in e['shares']))
            A[(s, R, 'killgold')].append(sum(e.get('gold', 0) for e in g['ev'] if e['k'] == 'death' and e['r'] <= R and e.get('by') is not None and team.get(e['by']) == t))
            A[(s, R, 'clears')].append(sum(1 for e in g['ev'] if e['k'] == 'group_clear' and e['r'] <= R and team.get(e.get('by')) == t))
            A[(s, R, 'earned')].append(sum(c['earned'][R - 1] or 0 for c in ch if c['team'] == t))
            if R == 100:
                fc = [e['r'] for e in g['ev'] if e['k'] == 'capture' and e.get('team') == t]
                A[(s, R, 'first_cap')].append(min(fc) if fc else 999)
                if s == 'F':
                    for c in ch:
                        if c['team'] == t: P[nm[c['id']]].append(c['earned'][R - 1] or 0)
for k in sorted(A):
    v = sorted(A[k]); print(k, len(v), 'mean', round(sum(v) / len(v), 1), 'median', v[len(v) // 2])
for k, v in sorted(P.items()): print('F r100 earned', k, len(v), round(sum(v) / len(v), 1))
