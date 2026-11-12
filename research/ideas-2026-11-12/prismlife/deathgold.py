"""Unspent gold and max health of our Prism when it dies, against all its rounds near enemies: python3 deathgold.py EXTROOT/TAG"""
import gzip, json, os, sys, statistics
from multiprocessing import Pool


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
    except Exception: return None
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']; idx = {q: i for i, q in enumerate(rounds)}
    pr = [c for c in ch if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    P = ch[pr[0]]; out = []
    for x in ev:
        if x['k'] == 'death' and x['v'] == pr[0] and x.get('by') is not None:
            i = idx.get(x['r'] - 1)
            if i is None or not P['alive'][i]: continue
            # the hit that killed: the overkill is unknown; the health before the last 2 rounds' hits
            out.append((x['r'], P['gold'][i], P['maxHp'][i], x.get('gems', 0), P['hp'][i]))
    return out


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    print(len(R), 'Prism deaths to champions')
    g = sorted(r[1] for r in R); n = len(g)
    print(f'  unspent gold at death: median {g[n // 2]}, p75 {g[3 * n // 4]}, p90 {g[9 * n // 10]}; 90+ (3 shards) {100 * sum(1 for x in g if x >= 90) / n:.0f}%, 150+ {100 * sum(1 for x in g if x >= 150) / n:.0f}%, 300+ {100 * sum(1 for x in g if x >= 300) / n:.0f}%')
    sh = sorted((r[1] // 30) * 65 / r[2] for r in R)
    print(f'  health that gold buys as Health shards, over max health: median {sh[n // 2]:.2f}, p75 {sh[3 * n // 4]:.2f}, p90 {sh[9 * n // 10]:.2f}; 25%+ of max health in {100 * sum(1 for x in sh if x >= 0.25) / n:.0f}% of deaths')
    for lo, hi in [(0, 300), (300, 600), (600, 3000)]:
        s = [r for r in R if lo <= r[0] < hi]
        if s: print(f'  deaths in rounds {lo}-{hi}: {len(s)}; max health median {statistics.median(r[2] for r in s):.0f}; unspent gold median {statistics.median(r[1] for r in s):.0f}, mean {statistics.mean(r[1] for r in s):.0f}; bag median {statistics.median(r[3] for r in s):.0f}')
