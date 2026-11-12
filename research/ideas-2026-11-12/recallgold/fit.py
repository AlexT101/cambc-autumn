"""Fit an enemy's carried gold at a kept recall we cancel on what a bot can read of it: the gold its stats show it
spent (shards = stat above base over growth, summed over the three stats, x 30), the round and the scores.

    python3 fit.py EXTDIR

The shard count is the one recall_worth() computes in the variants (Ryth's Strength from Health and Prism's
Focus from gems taken out first).
"""
import sys, os, json, gzip
from multiprocessing import Pool
import numpy as np

# cambc-rules.yaml champions: [base, growth] for health, strength, focus
STATS = {
    'Ryth': ((1200, 100), (45, 4.5), (100, 10)), 'Vesper Vale': ((1000, 100), (35, 5), (100, 10)),
    'Prism': ((700, 65), (35, 2.5), (90, 8)), 'Stellar': ((650, 65), (30, 3.5), (85, 8.5)),
    'Vendetta': ((900, 100), (65, 6), (100, 10)), 'Marcella': ((1200, 100), (40, 3.5), (60, 10)),
    'Tavi': ((900, 75), (45, 5), (110, 10)), 'Willow': ((700, 50), (55, 3), (140, 5)),
    'Ren': ((900, 100), (35, 5), (100, 9)), 'Varg': ((1000, 100), (50, 5), (100, 10)),
    'Heart of Ruin': ((1000, 100), (30, 3), (80, 9)), 'Cassi': ((600, 65), (30, 3), (100, 13)),
    'Issac': ((900, 80), (45, 3), (100, 10)),
}


def shards(name, mh, s, f, gems):
    (hb, hg), (sb, sg), (fb, fg) = STATS[name]
    dh = max(0.0, mh - hb)
    if name == 'Ryth': s -= 0.01 * dh
    if name == 'Prism': f -= 1.5 * gems
    return dh / hg + max(0.0, s - sb) / sg + max(0.0, f - fb) / fg


def one(d):
    try:
        meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception:
        return None
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {r: i for i, r in enumerate(rounds)}
    rows = []; prev = None
    for e in ev:
        if e['k'] == 'recall_cancel' and e.get('cause') in ('damage', 'stun') and e.get('left', 9) <= 3 and prev is not None \
                and prev['s'] == e['s'] and prev['k'] in ('attack', 'cast') and prev.get('a') in team \
                and team[prev['a']] == us and team[e['a']] != us and typ[e['a']] in STATS:
            a = e['a']; i = idx.get(e['r'] - 1, idx.get(e['r'])); c = ch[a]
            sh = shards(typ[a], c['maxHp'][i], c['str'][i], c['foc'][i], c['gems'][i])
            top = max(R['gems'][0][i], R['gems'][1][i])
            rows.append((c['gold'][i], 30 * sh, c['earned'][i] - c['gold'][i], e['r'], top, R['gems'][1 - us][i]))
        prev = e
    return rows


def main():
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(12) as pool: rows = [r for rs in pool.map(one, dirs, chunksize=8) if rs for r in rs]
    A = np.array(rows, dtype=float); y = A[:, 0]
    print(f'{len(A)} cancels; gold mean {y.mean():.1f}')
    for k, nm in [(1, 'spent from stats'), (2, 'spent true (earned-gold)'), (3, 'round'), (4, 'top score')]:
        X = np.column_stack([np.ones(len(A)), A[:, k]]); b, *_ = np.linalg.lstsq(X, y, rcond=None)
        r2 = 1 - (y - X @ b).var() / y.var()
        print(f'  {nm:26s} R2={r2:.3f} gold ~ {b[0]:.2f} + {b[1]:.5f} x   (x mean {A[:, k].mean():.0f})')
    print('  corr(stats spent, true spent)', np.corrcoef(A[:, 1], A[:, 2])[0, 1].round(3))
    for lo, hi in [(0, 300), (300, 600), (600, 900), (900, 1200), (1200, 1800), (1800, 99999)]:
        m = (A[:, 1] >= lo) & (A[:, 1] < hi); print(f'  stats-spent {lo}-{hi}: n={m.sum()} gold mean {y[m].mean():.0f} med {np.median(y[m]):.0f}')
    for lo, hi in [(0, 200), (200, 400), (400, 600), (600, 800), (800, 1001)]:
        m = (A[:, 4] >= lo) & (A[:, 4] < hi); print(f'  top score {lo}-{hi}: n={m.sum()} gold mean {y[m].mean():.0f}')


if __name__ == '__main__': main()
