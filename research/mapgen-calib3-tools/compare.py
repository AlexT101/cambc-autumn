# Ladder (first set) against generated sets on the ladder-v2 metric list, with tests.
#   python3 research/mapgen-calib3-tools/compare.py ladder=ladder.jsonl v1=v1.jsonl v2=v2.jsonl [--kind KIND]  (stats.mjs output)
# Numeric per-map metrics: KS distance and two-sample KS p (scipy). Binary per-map shares: two-sided binomial test of
# the ladder's count against the generated rate. Group-level shares are taken per map (maps weighted equally).
import json, sys, collections
import numpy as np
from scipy import stats

args = [a for a in sys.argv[1:] if not a.startswith('--')]
KIND = None
if '--kind' in sys.argv: KIND = sys.argv[sys.argv.index('--kind') + 1]; args = [a for a in args if a != KIND]
SETS = {}
for a in args:
    name, f = a.split('=', 1)
    rows = [json.loads(l) for l in open(f) if l.strip()]
    if KIND and name != 'ladder': rows = [r for r in rows if r.get('kind') in KIND.split(',')]
    SETS[name] = rows
REF = list(SETS)[0]
OTH = [n for n in SETS if n != REF]
MON = {'wolf', 'elk', 'golem', 'monolith'}
TYPES = ['wolf', 'elk', 'golem', 'monolith', 'gem_cluster', 'gold_cluster']


def gclass(t):
    mon = [k for k in t if k in MON]; cl = [k for k in t if k not in MON]
    if mon and cl: return 'guarded'
    if cl: return 'gem only' if set(cl) == {'gem_cluster'} else 'gold only' if set(cl) == {'gold_cluster'} else 'gem+gold'
    return 'monsters'


def derive(r):
    f = r['f']; gl = r['group_list']; sg = r['side_groups']
    t = collections.Counter()
    for q in gl:
        for k, v in q['types'].items(): t[k] += v
    camps = sum(t.values()) or 1
    sizes = [q['n'] for q in gl]; ng = max(1, len(gl))
    multi = [q for q in gl if q['n'] >= 3]
    cls = collections.Counter(gclass(q['types']) for q in gl)
    balls = [q for q in sg if q['pure_gem'] and q['n'] >= 3]
    pg = [q for q in sg if q['pure_gem']]
    d = {
        # size
        'area': f['area'], 'long side': max(r['W'], r['H']), 'short side': min(r['W'], r['H']), 'aspect': max(r['W'], r['H']) / min(r['W'], r['H']),
        # altars and sites
        'altar tiles': f['altars'], 'self-mirrored altars': sum(a['self'] for a in r['altar_list']), 'nearest altar ratio': f['altar_ratio'] if f['altar_ratio'] is not None else 0.5,
        'groups per side': f['groups_side'], 'camps per side': f['camps_side'], 'shared groups': f['shared_groups'], 'picks': r['picks'],
        # spawn distances
        'spawn walk dist': f['spawn_dist'], 'spawn_rel': f['spawn_rel'], 'detour': min(f['detour'], 6),
        'nearest group to spawn (cheb)': min([q['sd'] for q in gl] or [99]),
        # camp-type mix (share of camps)
        **{f'{k} share': t[k] / camps for k in TYPES},
        'gems per side': f['gems_side'], 'gold per side': f['gold_side'],
        # group make-up (share of a map's groups)
        **{f'groups: {c}': cls[c] / ng for c in ['guarded', 'gem only', 'gold only', 'gem+gold', 'monsters']},
        # sizes and shapes
        'mean group size': float(np.mean(sizes)) if sizes else 0, 'max group': max(sizes or [0]), 'single share': sum(s == 1 for s in sizes) / ng,
        'groups of 3+ share': len(multi) / ng,
        'line share (3+ groups)': (sum(min(q['bw'], q['bh']) == 1 for q in multi) / len(multi)) if multi else None,
        'bbox fill (3+ groups)': float(np.mean([q['n'] / (q['bw'] * q['bh']) for q in multi])) if multi else None,
        'elongation (3+ groups)': float(np.mean([max(q['bw'], q['bh']) / min(q['bw'], q['bh']) for q in multi])) if multi else None,
        'gem balls per side': len(balls), 'pure-gem singles share': (sum(q['n'] == 1 for q in pg) / len(pg)) if pg else None,
        # terrain
        'walls': f['walls'], 'holes': f['holes'], 'bushes': f['bushes'], 'reach_frac': f['reach_frac'],
    }
    b = {
        'W > H': r['W'] > r['H'], 'H > W': r['H'] > r['W'], 'long side < 35': max(r['W'], r['H']) < 35,
        'altars 1': f['altars'] == 1, 'altars 2': f['altars'] == 2, 'altars 3': f['altars'] == 3, 'altars 4': f['altars'] == 4, 'altars 5+': f['altars'] >= 5,
        'odd altar count': f['altars'] % 2 == 1, 'shared groups 0': f['shared_groups'] == 0, 'shared groups 2+': f['shared_groups'] >= 2,
        'picks 3': r['picks'] == 3, 'picks 5': r['picks'] == 5,
        'spawn 3x3': r['spawn_wh'] == '3x3', 'rotational': r['sym'] == 'rotational',
        'golem present': t['golem'] > 0, 'monolith present': t['monolith'] > 0, 'elk present': t['elk'] > 0, 'no gold (gem-only)': f['gold_side'] == 0,
        'a gem ball (pure gem, 3+)': len(balls) > 0, 'a shared gem ball': any(q['shared'] for q in balls), '2+ gem balls': len(balls) >= 2,
        'no singleton groups': d['single share'] == 0, 'group of 10+': d['max group'] >= 10, 'group of 20+': d['max group'] >= 20,
        'camp group <= 3 of spawn': d['nearest group to spawn (cheb)'] <= 3,
        'no walls': f['walls'] == 0, 'no holes': f['holes'] == 0, 'no bushes': f['bushes'] == 0, 'holes > 0.15': f['holes'] > 0.15,
        'walls > 0.15': f['walls'] > 0.15, 'bushes > 0.08': f['bushes'] > 0.08, 'detour >= 2': f['detour'] >= 2,
    }
    return d, b, sizes, gl


D = {s: [derive(r) for r in rows] for s, rows in SETS.items()}


def fmt(v):
    if v != v: return '-'
    if abs(v) >= 100: return f'{v:.0f}'
    if abs(v) >= 10: return f'{v:.1f}'
    return f'{v:.2f}'


def pf(p): return f'{p:.0e}' if p < 0.001 else f'{p:.3f}'


print('Sets: ' + ', '.join(f'{s} {len(v)}' for s, v in D.items()) + (f' (kind {KIND})' if KIND else ''))
print('\n### Numeric (p10 / p50 / p90; mean) and KS vs ladder (D, p)\n')
print('| metric | ' + ' | '.join(SETS) + ' | ' + ' | '.join(f'{o} D (p)' for o in OTH) + ' |')
print('|' + '---|' * (1 + len(SETS) + len(OTH)))
summ = {o: [] for o in OTH}
for k in D[REF][0][0]:
    cols, vals = [], {}
    for s in SETS:
        a = np.array([x[0][k] for x in D[s] if x[0][k] is not None], float); vals[s] = a
        cols.append('/'.join(fmt(np.quantile(a, p)) for p in (0.1, 0.5, 0.9)) + f'; {fmt(a.mean())}' if len(a) else '-')
    ks = {}
    for o in OTH:
        r = stats.ks_2samp(vals[REF], vals[o]); ks[o] = r; summ[o].append((r.pvalue, r.statistic, k))
    print(f'| {k} | ' + ' | '.join(cols) + ' | ' + ' | '.join(f'{ks[o].statistic:.2f} ({pf(ks[o].pvalue)})' for o in OTH) + ' |')

print('\n### Shares of maps, binomial test of the ladder count at the generated rate\n')
print('| property | ' + ' | '.join(SETS) + ' | ' + ' | '.join(f'{o} p' for o in OTH) + ' |')
print('|' + '---|' * (1 + len(SETS) + len(OTH)))
bsum = {o: [] for o in OTH}
for k in D[REF][0][1]:
    rates = {s: np.mean([x[1][k] for x in D[s]]) for s in SETS}
    kref = int(sum(x[1][k] for x in D[REF])); n = len(D[REF])
    ps = {}
    for o in OTH:
        p = rates[o]; ps[o] = stats.binomtest(kref, n, min(max(p, 1e-6), 1 - 1e-6)).pvalue if 0 < p < 1 else (1.0 if (p == 0 and kref == 0) or (p == 1 and kref == n) else 0.0)
        bsum[o].append((ps[o], k))
    print(f'| {k} | ' + ' | '.join(f'{100 * rates[s]:.0f}%' for s in SETS) + ' | ' + ' | '.join(pf(ps[o]) for o in OTH) + ' |')


def sizeh(s):
    tot = collections.Counter()
    for _, _, sizes, _ in D[s]:
        for z in sizes: tot[min(z, 7)] += 1 / max(1, len(sizes))
    return '/'.join(f'{100 * tot[k] / len(D[s]):.0f}' for k in range(1, 8))


print('\n| group sizes 1/2/3/4/5/6/7+ (share of a map\'s groups) | ' + ' | '.join(sizeh(s) for s in SETS) + ' |')
for o in OTH:
    a = sorted(summ[o]); b = sorted(bsum[o])
    print(f'\n{o}: mean KS D {np.mean([x[1] for x in summ[o]]):.3f}; numeric p<0.01: {sum(x[0] < 0.01 for x in a)} of {len(a)} '
          f'({", ".join(f"{k} {pf(p)}" for p, _, k in a if p < 0.01)}); shares p<0.01: {sum(x[0] < 0.01 for x in b)} of {len(b)} '
          f'({", ".join(f"{k} {pf(p)}" for p, k in b if p < 0.01)})')
