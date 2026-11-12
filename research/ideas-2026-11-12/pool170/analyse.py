"""Win rates of three bots against the Fish/Mite bodies on the 40 new 05 maps (replays/ab/p170-*) and on the pinned 128
(their fgate runs' ladder suites), per-map outliers, and a paired c520-ps - chy-life read on both.
    python3 research/ideas-2026-11-12/pool170/analyse.py > research/ideas-2026-11-12/pool170/results.md"""
import collections, json, math, re
from pathlib import Path

R = Path(__file__).resolve().parents[3]
BOTS = {'c520-ps': ('c520-ps', range(75, 87), '-fuel100000'), 'chy-life': ('chy-life', range(75, 87), '-fuel100000'),
        'oc-dfuel-506': ('dfuel-506', range(0, 34), '')}
BODIES = ('Flp4', 'Mt3q')


def batch_dir(run, suite):
    for s in json.loads((R / f'replays/ab/{run}/summary.json').read_text())['suites']:
        if s['suite'] == suite: return R / s['batch']


def games(run, suite):
    """(map stem, side of our bot, noise k) -> 1/0.5/0 for our bot (bot index 0)."""
    out = {}
    for m in json.loads((batch_dir(run, suite) / 'results.json').read_text())['matches']:
        if m.get('winner') is None: continue
        stem = Path(m['map']).stem; k = (m['runtime_config'] or {}).get('a') or (m['runtime_config'] or {}).get('b')
        side = 'a' if m['order'][0] == 0 else 'b'
        out[(stem, side, k['salt'] if k else None)] = 1.0 if m['winner'] == 0 else 0.0
    return out


def wilson(w, n, z=1.96):
    if not n: return (0, 0, 0)
    p = w / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * p, 100 * (c - h), 100 * (c + h)


def fmt(w, n):
    p, lo, hi = wilson(w, n); return f'{p:.1f}% ({lo:.1f}-{hi:.1f}) of {n:,}'


new, old = {}, {}
for bot, (tag, batches, fuel) in BOTS.items():
    for o in BODIES:
        new[bot, o] = {(re.sub(r'-k\d{3}$', '', s), side, k): v for (s, side, k), v in games(f'p170-{bot}-{o}', 'maps').items()}
        old[bot, o] = {}
        for j in batches:
            run = f'fbe501-{tag}-{o}-m2560b{j:03d}{fuel}'
            if (R / f'replays/ab/{run}/summary.json').exists(): old[bot, o].update(games(run, 'ladder'))

print('## Results against the Fish and Mite bodies: new 05 maps against the pinned 128\n')
print('| bot | body | 05 maps (40) | old 128 | 05 minus 128 |')
print('|---|---|---|---|---|')
for bot in BOTS:
    for o in (*BODIES, 'both'):
        os_ = BODIES if o == 'both' else (o,)
        a = [v for x in os_ for v in new[bot, x].values()]; b = [v for x in os_ for v in old[bot, x].values()]
        pa, pb = 100 * sum(a) / len(a), 100 * sum(b) / len(b)
        se = 100 * math.hypot(math.sqrt(pa / 100 * (1 - pa / 100) / len(a)), math.sqrt(pb / 100 * (1 - pb / 100) / len(b)))
        print(f'| {bot} | {o} | {fmt(sum(a), len(a))} | {fmt(sum(b), len(b))} | {pa - pb:+.1f} ±{1.96 * se:.1f} |')

print('\nOld-128 reads: c520-ps and chy-life from fgate batches b075-b086 (ladder noise 76-87, the seeds the 05 runs use);'
      ' oc-dfuel-506 from b000-b033 (noise 1-34). Noise seeds are draws of the same body population.\n')

# Per-map: each bot's win % over both bodies (12 seeds x 2 sides x 2 bodies = 48 games a map).
print('## Per map (05), win % over 48 games a bot (both bodies, both sides, 12 seeds)\n')
maps = sorted({m for (m, _, _) in new['c520-ps', 'Flp4']})
rows = []
for m in maps:
    r = {}
    for bot in BOTS:
        for o in BODIES:
            v = [x for (mm, _, _), x in new[bot, o].items() if mm == m]; r[bot, o] = 100 * sum(v) / len(v)
        r[bot] = (r[bot, 'Flp4'] + r[bot, 'Mt3q']) / 2
    rows.append((r['c520-ps'], m, r))
print('| map | c520-ps (F / M) | chy-life (F / M) | oc-dfuel-506 (F / M) |')
print('|---|---|---|---|')
for _, m, r in sorted(rows):
    print(f'| {m} | ' + ' | '.join(f"{r[b]:.0f} ({r[b, 'Flp4']:.0f} / {r[b, 'Mt3q']:.0f})" for b in BOTS) + ' |')

# Paired c520-ps - chy-life on the same (map, side, seed) cells, units by map.
print('\n## Paired c520-ps minus chy-life (same map, side and seed), units by map\n')
for label, src in (('05 maps', new), ('old 128 (b075-b086)', old)):
    per = collections.defaultdict(list)
    for o in BODIES:
        x, y = src['c520-ps', o], src['chy-life', o]
        for c in x.keys() & y.keys(): per[c[0]].append(x[c] - y[c])
    u = [100 * sum(v) / len(v) for v in per.values()]
    mu = sum(u) / len(u); sd = math.sqrt(sum((a - mu) ** 2 for a in u) / (len(u) - 1))
    print(f'- {label}: {mu:+.2f} ±{1.96 * sd / math.sqrt(len(u)):.2f} points over {len(u)} maps ({sum(len(v) for v in per.values()):,} paired games)')
