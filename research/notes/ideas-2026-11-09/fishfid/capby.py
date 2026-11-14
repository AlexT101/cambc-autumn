"""Fish-side capture shares by r100/r200: count and gold by recipient, and gold per share."""
import sys, os, collections
sys.path.insert(0, '/home/ubuntu/tmp-offload/fishre/tools')
from fl import games, US
filt = None if os.environ.get('LOCAL') else (lambda g: g['opp'] == US and g['created'] >= '2026-11-08T16')
R = int(os.environ.get('R', '200')); N = 0
C = collections.defaultdict(lambda: [0, 0, 0]); G = collections.defaultdict(lambda: [0, 0, 0])
for g in games(filt, rounds=False):
    N += 1; F = g['fish']; nm = {c['id']: c['name'] for c in g['meta']['champions']}
    for e in g['ev']:
        if e['k'] == 'capture' and e['r'] <= R and e.get('team') == F:
            for a, gems, gold in e['shares']:
                k = nm.get(a, a); C[k][0] += 1; C[k][1] += gold; C[k][2] += gems
            G[e['g']][0] += 1
for k, (n, gold, gems) in sorted(C.items(), key=lambda x: -x[1][1]): print(f'{k:14s} shares/g {n/N:.2f} gold/g {gold/N:6.1f} gold/share {gold/max(n,1):6.1f} gems/share {gems/max(n,1):5.1f}')
