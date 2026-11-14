import sys, os, collections
sys.path.insert(0, '/home/ubuntu/tmp-offload/fishre/tools')
from fl import games, US
filt = None if os.environ.get('LOCAL') else (lambda g: g['opp'] == US and g['created'] >= '2026-11-08T16')
R = int(os.environ.get('R', '600')); C = collections.Counter(); T = collections.Counter(); N = 0
for g in games(filt, rounds=False):
    N += 1; F = g['fish']
    for e in g['ev']:
        if e['k'] == 'capture' and e['r'] <= R:
            s = 'F' if e.get('team') == F else 'O'
            C[(s, len(e['shares']))] += 1; T[(s, 'gold')] += sum(x[2] for x in e['shares']); T[(s, 'n')] += 1
for s in 'FO':
    n = T[(s, 'n')]; print(s, 'captures/g', round(n / N, 2), 'gold/capture', round(T[(s, 'gold')] / n, 1), ' '.join(f'{k}:{C[(s, k)] / n:.2f}' for k in range(1, 5)))
