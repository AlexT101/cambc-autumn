"""Paired real-budget counts and map-cluster bootstrap (both sides stay together).
paired.py BASE.json CAND.json BASE-run-batch.log CAND-run-batch.log OUT.json
"""
import collections
import json
import re
import sys
from pathlib import Path
import numpy as np


def read(data, log):
    counts, pending = {}, None
    for line in Path(log).read_text().splitlines():
        if m := re.search(r'Out of fuel: A (\d+) B (\d+)', line):
            pending = tuple(map(int, m.groups()))
        elif pending is not None and 'Replay: ' in line:
            name = Path(line.split('Replay: ', 1)[1]).parent.name
            map_, side = name.rsplit('-', 1)
            counts[map_, side] = pending[side == 'b']
            pending = None
    d = json.loads(Path(data).read_text())
    out, labels, drafts = {}, collections.Counter(), collections.Counter()
    broken = []
    for g in d['games']:
        assert 'error' not in g, g
        key = g['map'], g['side']
        sc = {k: v for k, v in g['shortcuts'].items() if k != 'out-of-fuel' and 'SLOT' not in k}
        labels.update(sc)
        drafts.update(g['draft'])
        out[key] = [counts[key], sum(sc.values()), sum(g['play']), len(g['play'])]
        if g['handoff'] or g['capped'] or len(g['play']) <= 5 * g['bodies']:
            broken.append([*key, g['handoff'], g['capped'], len(g['play'])])
    return out, {'shortcuts_by_label': labels, 'drafts': drafts, 'broken_capped_or_early': broken,
                 'after_round1': d['all'], 'opponent': d['opp'], 'test_draft': d['test_draft']}


a, ma = read(sys.argv[1], sys.argv[3])
b, mb = read(sys.argv[2], sys.argv[4])
assert a.keys() == b.keys()
assert ma['opponent'] == mb['opponent'] and ma['test_draft'] == mb['test_draft']
by_map = collections.defaultdict(lambda: np.zeros(8, dtype=np.float64))
for key in a:
    by_map[key[0]] += a[key] + b[key]
rows = np.array([by_map[k] for k in sorted(by_map)])

def metrics(s):
    x, y = s[..., :4], s[..., 4:]
    return np.stack((y[..., 0] / x[..., 0] - 1, y[..., 1] / x[..., 1] - 1,
                     (y[..., 2] / y[..., 3]) / (x[..., 2] / x[..., 3]) - 1,
                     (y[..., 0] / y[..., 3]) / (x[..., 0] / x[..., 3]) - 1,
                     (y[..., 1] / y[..., 3]) / (x[..., 1] / x[..., 3]) - 1), axis=-1)

rng = np.random.default_rng(20261111)
boots = []
for _ in range(100):
    indices = rng.integers(len(rows), size=(100, len(rows)))
    boots.append(metrics(rows[indices].sum(axis=1)))
ci = np.quantile(np.concatenate(boots), [0.025, 0.975], axis=0).T
sums = rows.sum(axis=0)
names = ['OOF', 'shortcuts', 'mean_fuel', 'OOF_per_turn', 'shortcuts_per_turn']
point = metrics(sums)
result = {'games': len(a), 'maps': len(rows), 'bootstrap': {'resamples':10000, 'unit':'paired map (both sides)', 'seed':20261111},
          'baseline': {'totals': dict(zip(['OOF','shortcuts','fuel','turns'], sums[:4].astype(int).tolist())), **ma},
          'candidate': {'totals': dict(zip(['OOF','shortcuts','fuel','turns'], sums[4:].astype(int).tolist())), **mb},
          'relative_changes': {name: {'estimate': float(point[i]), 'ci95': ci[i].tolist()} for i,name in enumerate(names)},
          'pairs': [{'map':key[0], 'side':key[1], 'baseline':a[key], 'candidate':b[key]} for key in sorted(a)]}
pairs = result.pop('pairs')
header = json.dumps(result, indent=2).rsplit('\n}', 1)[0]
body = ',\n'.join('    ' + json.dumps(row, separators=(',', ':')) for row in pairs)
Path(sys.argv[5]).write_text(header + ',\n  "pairs": [\n' + body + '\n  ]\n}\n')
print(f'{len(a)} paired games, {len(rows)} map clusters')
print(result['baseline']['totals'], '->', result['candidate']['totals'])
for i,name in enumerate(names): print(f'{name}: {100*point[i]:+.2f}% (95% CI {100*ci[i,0]:+.2f} .. {100*ci[i,1]:+.2f})')
