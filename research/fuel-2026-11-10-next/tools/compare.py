"""Paired real-budget bench results, using the runner's complete OOF counts.
Usage: compare.py BASE.json CAND.json BASE-run-batch.log CAND-run-batch.log
"""
import json, random, re, sys
from pathlib import Path

def read(data, log):
    counts = {}
    pending = None
    for line in Path(log).read_text().splitlines():
        if m := re.search(r'Out of fuel: A (\d+) B (\d+)', line):
            pending = tuple(map(int, m.groups()))
        elif pending is not None and 'Replay: ' in line:
            name = Path(line.split('Replay: ', 1)[1]).parent.name
            map_, side = name.rsplit('-', 1)
            counts[map_, side] = pending[side == 'b']
            pending = None
    games = json.loads(Path(data).read_text())['games']
    out = {}
    for g in games:
        assert 'error' not in g, g
        key = g['map'], g['side']
        sc = sum(v for k, v in g['shortcuts'].items() if k != 'out-of-fuel' and 'SLOT' not in k)
        out[key] = counts[key], sc, sum(g['play']), len(g['play'])
    return out

a, b = read(sys.argv[1], sys.argv[3]), read(sys.argv[2], sys.argv[4])
assert a.keys() == b.keys()
keys = sorted(a)
rows = [(*a[k], *b[k]) for k in keys]
def calc(idx):
    sums = [sum(rows[i][j] for i in idx) for j in range(8)]
    aa, bb = sums[:4], sums[4:]
    values = [bb[0]/aa[0]-1, bb[1]/aa[1]-1, (bb[2]/bb[3])/(aa[2]/aa[3])-1,
              (bb[0]/bb[3])/(aa[0]/aa[3])-1, (bb[1]/bb[3])/(aa[1]/aa[3])-1]
    return aa, bb, values
n = len(rows)
aa, bb, point = calc(range(n))
rng = random.Random(1001)
boot = [calc([rng.randrange(n) for _ in range(n)])[2] for _ in range(1000)]
print(f'{n} paired games; OOF {aa[0]} -> {bb[0]}; shortcuts {aa[1]} -> {bb[1]}; turns {aa[3]} -> {bb[3]}')
for j, name in enumerate(('OOF turns','shortcuts excluding OOF','mean fuel','OOF per turn','shortcuts per turn')):
    x = sorted(row[j] for row in boot)
    print(f'{name:24s} {100*point[j]:+.2f}% (95% CI {100*x[25]:+.2f} .. {100*x[974]:+.2f})')
