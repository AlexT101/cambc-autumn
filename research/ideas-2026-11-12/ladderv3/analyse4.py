"""The step-3 bots on ladder-v4 (pool-v4 b000-b003) beside ladder-v3 (pool-v3 b000-b003) and ladder-v2 (b073-b074,
b087-b088): win rates against the Fish and Mite bodies, paired differences between bots, and win rates by the
full-pool features (close spawns, open frame, hole-framed arena) on both v3 and v4 maps.
    python3 research/ideas-2026-11-12/ladderv3/analyse4.py > research/ideas-2026-11-12/ladderv3/fullpool/results.md"""
import collections, glob, json, math, os, sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(R / 'tools'))
import ladder_set  # noqa: E402

BOTS = ('c520-ps', 'chy-life', 'dfuel-506')
BODIES = ('Flp4', 'mf-c1-lv3')
POOLS = {'v2': ((73, 74, 87, 88), ''), 'v3': (range(0, 4), '-Pv3'), 'v4': (range(0, 4), '-Pv4')}
GEN = {'v3': 'generated-v3', 'v4': 'generated-v4'}
L128 = set(ladder_set.names('128'))
HOME = Path(os.path.expanduser('~/tmp-offload/gatebatch'))


def games(run):
    s = json.loads((R / f'replays/ab/{run}/summary.json').read_text())
    out = {}
    for su in s['suites']:
        for m in json.loads((R / su['batch'] / 'results.json').read_text())['matches']:
            if m.get('winner') is None: continue
            out[Path(m['map']).stem, 'a' if m['order'][0] == 0 else 'b'] = 1.0 if m['winner'] == 0 else 0.0
    return out


def metrics(pool):
    out = {}
    for ix in (HOME / GEN[pool]).glob('*/index.json'):
        for m in json.loads(ix.read_text())['maps']: out[m['file'].removesuffix('.map26a')] = m['metrics']
    return out


def wilson(w, n, z=1.96):
    p = w / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * p, 100 * (c - h), 100 * (c + h)


def fmt(v):
    if not v: return '-'
    p, lo, hi = wilson(sum(v), len(v)); return f'{p:.1f}% ({lo:.1f}-{hi:.1f}) of {len(v):,}'


G = {}
for bot in BOTS:
    for body in BODIES:
        for pool, (js, tag) in POOLS.items():
            G[bot, body, pool] = {}
            for j in js:
                runs = glob.glob(str(R / f'replays/ab/fb*-{bot}-{body}-m2560b{j:03d}-fuel100000{tag}/summary.json'))
                if len(runs) != 1: raise SystemExit(f'{bot} {body} {pool} b{j:03d}: {len(runs)} runs')
                G[bot, body, pool].update({(k[0] if k[0] not in L128 else f'{k[0]}@{j}', k[1]): v for k, v in games(Path(runs[0]).parent.name).items()})
fresh = lambda bot, body, pool: {k: v for k, v in G[bot, body, pool].items() if k[0].split('@')[0] not in L128}

print('## Win rates against both bodies on fresh maps (fgate batches at 100k fuel, bodies unmetered; 10,240 maps a pool, both sides)\n')
print('| bot | v2 | v3 | v4 | v4 minus v3 |')
print('|---|---|---|---|---|')
for bot in BOTS:
    c = {p: [v for body in BODIES for v in fresh(bot, body, p).values()] for p in POOLS}
    pa, pb = 100 * sum(c['v4']) / len(c['v4']), 100 * sum(c['v3']) / len(c['v3'])
    se = 100 * math.hypot(math.sqrt(pa / 100 * (1 - pa / 100) / len(c['v4'])), math.sqrt(pb / 100 * (1 - pb / 100) / len(c['v3'])))
    print(f'| {bot} | ' + ' | '.join(fmt(c[p]) for p in POOLS) + f' | {pa - pb:+.1f} ±{1.96 * se:.1f} |')

print('\n## Paired differences between bots on fresh maps (same map, side and body; units are maps, 95% CI)\n')
print('| pair | ' + ' | '.join(POOLS) + ' |')
print('|---|' + '---|' * len(POOLS))
for x, y in (('c520-ps', 'chy-life'), ('c520-ps', 'dfuel-506'), ('chy-life', 'dfuel-506')):
    row = []
    for p in POOLS:
        per = collections.defaultdict(list)
        for body in BODIES:
            cx, cy = fresh(x, body, p), fresh(y, body, p)
            for k in cx.keys() & cy.keys(): per[k[0]].append(cx[k] - cy[k])
        u = [100 * sum(v) / len(v) for v in per.values()]
        mu = sum(u) / len(u); sd = math.sqrt(sum((t - mu) ** 2 for t in u) / (len(u) - 1))
        row.append(f'{mu:+.2f} ±{1.96 * sd / math.sqrt(len(u)):.2f}')
    print(f'| {x} - {y} | ' + ' | '.join(row) + ' |')

BUCKETS = {
    'close spawns (spawn_rel < 0.5)': lambda m: m['spawn_rel'] < 0.5,
    'other spawns': lambda m: m['spawn_rel'] >= 0.5,
    'open frame (fill_edge 1)': lambda m: m['fill_edge'] >= 1,
    'arena (fill_edge < 0.5)': lambda m: m['fill_edge'] < 0.5,
    'partly blocked frame': lambda m: 0.5 <= m['fill_edge'] < 1,
}
print('\n## Win rates by feature, both bodies (every fresh map, by the metrics its suite index records)\n')
M = {p: metrics(p) for p in GEN}
print('| bucket | pool | share of fresh maps | ' + ' | '.join(BOTS) + ' |')
print('|---|---|---|' + '---|' * len(BOTS))
for b, f in BUCKETS.items():
    for p in GEN:
        keep = {s for s, m in M[p].items() if f(m)}
        allg = {k[0] for k in fresh(BOTS[0], BODIES[0], p)}
        share = len(keep & allg) / max(1, len(allg & set(M[p])))
        row = [fmt([v for body in BODIES for k, v in fresh(bot, body, p).items() if k[0] in keep]) for bot in BOTS]
        print(f'| {b} | {p} | {100 * share:.1f}% | ' + ' | '.join(row) + ' |')
