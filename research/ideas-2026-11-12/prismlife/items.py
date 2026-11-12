"""What our Prism owns at rounds 300 and 600 (emblems and shards by family and stat): python3 items.py EXTROOT/TAG"""
import collections, gzip, json, os, sys
from multiprocessing import Pool


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
    except Exception: return None
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    pr = [c for c in R['champions'] if typ[c['id']] == 'Prism' and team[c['id']] == us]
    if not pr: return None
    P = pr[0]; out = {}
    for q in (300, 600):
        if q in R['round']:
            i = R['round'].index(q); it = P['items'][i]
            out[q] = {it[k]: it[k + 1] for k in range(0, len(it), 2)}
    return out


if __name__ == '__main__':
    root = sys.argv[1]
    en = json.load(open(os.path.join(root, 'enums.json')))['items']
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for r in pool.map(one, dirs, chunksize=8) if r]
    for q in (300, 600):
        S = [r[q] for r in R if q in r]
        c = collections.Counter(); have = collections.Counter()
        for s in S:
            for k, v in s.items():
                c[en[k]] += v; have[en[k]] += 1
        print(f'round {q}: {len(S)} Prisms; items a Prism (share owning):')
        for k, v in c.most_common(18): print(f'    {k:34s} {v / len(S):5.2f}  ({100 * have[k] / len(S):4.1f}%)')
