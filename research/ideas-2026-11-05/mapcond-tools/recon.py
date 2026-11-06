"""Rebuild each SPSA iteration's sign vectors, c_k and games from tune.py's seeded plan, and check them against the
x updates in history.jsonl. Writes RUN-iters.json: per iteration k, deltas, cn, the per-pair score difference, maps."""
import json, random, sys
from pathlib import Path
ROOT = Path('/home/ubuntu/cambc-autumn')
run = ROOT / 'replays/tune' / sys.argv[1]
out = Path(sys.argv[2])
cfg = json.loads((run / 'config.json').read_text())

def maps_in(pool):
    maps = []
    for d in pool:
        p = ROOT / d
        maps += sorted(p.glob('*.map26a')) if p.is_dir() else []
    return maps
MAPS = maps_in(cfg['pool'])

def plan(k):
    rng = random.Random(cfg['seed'] * 1000003 + k)
    ck = cfg['c'] / (k + 1) ** cfg['gamma']
    names = list(cfg['params'])
    cn = {n: max(ck, 1.0 / max(1, hi - lo)) if kind == 'int' else ck for n, (lo, hi, kind) in cfg['params'].items()}
    deltas = [{n: rng.choice((-1, 1)) for n in names} for _ in range(cfg['pairs'])]
    games = [(m, opp, rng.randrange(2)) for m in rng.sample(MAPS, cfg['maps_per_iter']) for opp in cfg['opps']]
    return deltas, cn, games

hist = [json.loads(l) for l in (run / 'history.jsonl').read_text().splitlines()]
names = list(cfg['params'])
recs, errs = [], []
for i, h in enumerate(hist):
    k = h['k'] - 1
    deltas, cn, games = plan(k)
    diffs = [h['mean'][f'p{p}'] - h['mean'][f'm{p}'] for p in range(cfg['pairs'])]
    if i > 0:
        xp = hist[i - 1]['x']
        ak = cfg['a'] / (k + 1 + cfg['A']) ** cfg['alpha']
        for n in names:
            g = sum(diffs[p] / (2 * cn[n] * deltas[p][n]) for p in range(cfg['pairs'])) / cfg['pairs']
            pred = min(1.0, max(0.0, xp[n] + ak * g))
            errs.append(abs(pred - h['x'][n]))
    recs.append({'k': h['k'], 'deltas': [[d[n] for n in names] for d in deltas], 'cn': [cn[n] for n in names],
                 'diffs': diffs, 'means': h['mean'], 'maps': [str(m.relative_to(ROOT)) for m, _, _ in games[::len(cfg['opps'])]],
                 'sides': [s for _, _, s in games]})
errs.sort()
print(f"{sys.argv[1]}: {len(hist)} iterations, {len(MAPS)} pool entries; |x pred - x| median {errs[len(errs)//2]:.2e}, "
      f"99% {errs[int(.99*len(errs))]:.2e}, max {errs[-1]:.2e}, >1e-6: {sum(e > 1e-6 for e in errs)} of {len(errs)}")
json.dump({'names': names, 'params': cfg['params'], 'opps': cfg['opps'], 'iters': recs}, out.open('w'))
