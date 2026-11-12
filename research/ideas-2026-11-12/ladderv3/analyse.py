"""Three bots against the Fish and Mite bodies on four ladder-v3 fgate batches (pool-v3 b000-b003) and four ladder-v2 ones (b073-b074, b087-b088):
win rates by part (v3's ladder-v2 part and 05 part, v2's maps, the pinned 128) and paired differences between bots.
    python3 research/ideas-2026-11-12/ladderv3/analyse.py > research/ideas-2026-11-12/ladderv3/results.md"""
import collections, glob, json, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(R / 'tools'))
import ladder_set  # noqa: E402

BOTS = ('c520-ps', 'chy-life', 'dfuel-506')
BODIES = ('Flp4', 'mf-c1-lv3')
# Four batches a pool: pool-v3 b000-b003, and the v2 pool's b073-b074 and b087-b088 (its last whole batches; no gate had
# played these four with these bots at --fuel 100000).
POOLS = {'v3': (range(0, 4), '-Pv3'), 'v2': ((73, 74, 87, 88), '')}
L128 = set(ladder_set.names('128'))


def is05(name): return name.startswith('gen-ladder05-') or name.startswith('mut-05')


def part(stem, pool):
    if stem.split('@')[0] in L128: return 'ladder 128'
    return ('v3: 05 part' if is05(stem) else 'v3: v2 part') if pool.startswith('v3') else 'v2'


def games(run):
    """(part, map stem, side) -> 1/0.5/0 for bot 0."""
    s = json.loads((R / f'replays/ab/{run}/summary.json').read_text())
    out = {}
    for su in s['suites']:
        for m in json.loads((R / su['batch'] / 'results.json').read_text())['matches']:
            if m.get('winner') is None: continue
            out[Path(m['map']).stem, 'a' if m['order'][0] == 0 else 'b'] = 1.0 if m['winner'] == 0 else 0.0
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
                # Ladder maps recur every batch (noise j + 1): key them by batch.
                G[bot, body, pool].update({(k[0] if k[0] not in L128 else f'{k[0]}@{j}', k[1]): v for k, v in games(Path(runs[0]).parent.name).items()})

PARTS = ('v2', 'v3: v2 part', 'v3: 05 part', 'v3 all fresh', 'ladder 128')


def sel(bot, body, pool, p):
    g = G[bot, body, pool]
    if p == 'v3 all fresh': return {k: v for k, v in g.items() if part(k[0], pool) != 'ladder 128'}
    return {k: v for k, v in g.items() if part(k[0], pool) == p}


def cells(bot, bodies, p):
    out = {}
    for body in bodies:
        for pool in POOLS:
            if p == 'ladder 128' or (p == 'v2') == pool.startswith('v2'):
                out.update({(body, pool, *k): v for k, v in sel(bot, body, pool, p).items()})
    return out


print('## Win rates against the bodies (fgate batches at 100k fuel, bodies unmetered)\n')
print('Fresh maps: v2 = the ladder-v2 pool\'s batches b073-b074 and b087-b088 (10,240 maps); v3 = pool-v3 batches b000-b003 (10,240 maps, '
      f'{sum(1 for k in G[BOTS[0], BODIES[0], "v3"] if is05(k[0])) // 2:,} of them the 05 part). Ladder 128: all eight batches\' side reads '
      '(noise 1-4, 74-75 and 88-89).\n')
for bodies, label in ((('Flp4',), 'Fish (rt-Flp4)'), (('mf-c1-lv3',), 'Mite (mf-c1, frozen as mf-c1-lv3)'), (BODIES, 'both bodies')):
    print(f'### {label}\n')
    print('| bot | ' + ' | '.join(PARTS) + ' | v3 minus v2 (fresh) |')
    print('|---|' + '---|' * (len(PARTS) + 1))
    for bot in BOTS:
        c = {p: list(cells(bot, bodies, p).values()) for p in PARTS}
        a, b = c['v3 all fresh'], c['v2']
        pa, pb = 100 * sum(a) / len(a), 100 * sum(b) / len(b)
        se = 100 * math.hypot(math.sqrt(pa / 100 * (1 - pa / 100) / len(a)), math.sqrt(pb / 100 * (1 - pb / 100) / len(b)))
        print(f'| {bot} | ' + ' | '.join(fmt(c[p]) for p in PARTS) + f' | {pa - pb:+.1f} ±{1.96 * se:.1f} |')
    print()

print('## Paired differences between bots (same map, side and body; units are maps, 95% CI)\n')
print('| pair | ' + ' | '.join(PARTS) + ' |')
print('|---|' + '---|' * len(PARTS))
for x, y in (('c520-ps', 'chy-life'), ('c520-ps', 'dfuel-506'), ('chy-life', 'dfuel-506')):
    row = []
    for p in PARTS:
        cx, cy = cells(x, BODIES, p), cells(y, BODIES, p)
        per = collections.defaultdict(list)
        for k in cx.keys() & cy.keys(): per[k[1], k[2]].append(cx[k] - cy[k])
        u = [100 * sum(v) / len(v) for v in per.values()]
        mu = sum(u) / len(u); sd = math.sqrt(sum((t - mu) ** 2 for t in u) / (len(u) - 1))
        row.append(f'{mu:+.2f} ±{1.96 * sd / math.sqrt(len(u)):.2f} ({len(u):,})')
    print(f'| {x} - {y} | ' + ' | '.join(row) + ' |')
