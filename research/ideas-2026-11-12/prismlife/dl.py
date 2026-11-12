"""The Prism's decision letters in the rounds before each death (debug builds' D lines): python3 dl.py EXTROOT/TAG"""
import collections, gzip, json, os, sys, zipfile
from multiprocessing import Pool
ROOT = '/home/ubuntu/cambc-autumn'


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception as e:
        return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    pr = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not pr: return []
    p = pr[0]; D = {}
    for line in out.splitlines():
        v = line.split()
        if len(v) >= 4 and v[0] == 'D' and v[2] == str(p): D[int(v[1])] = v[3]
    return [(x['r'], x.get('gems', 0), [D.get(q, '.') for q in range(x['r'] - 8, x['r'] + 1)]) for x in ev if x['k'] == 'death' and x['v'] == p and x.get('by') is not None]


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    print(len(R), 'deaths to champions')
    for k in range(9):
        c = collections.Counter(r[2][k] for r in R)
        print(f'  {8 - k} before:', ', '.join(f'{a} {100 * b / len(R):.0f}%' for a, b in c.most_common(8)))
    # the first round of the final unbroken run of R decisions (dots = no D line: dead, stunned turns print too)
    runs = collections.Counter()
    for r in R:
        s = r[2][:-1] if r[2][-1] == '.' else r[2]
        n = 0
        for a in reversed(s):
            if a == 'R': n += 1
            else: break
        runs[min(n, 8)] += 1
    print('rounds of retreat (R) straight before the death:', ', '.join(f'{k}: {100 * v / len(R):.0f}%' for k, v in sorted(runs.items())))
    pat = collections.Counter(''.join(r[2][-5:]) for r in R)
    print('commonest last five:', ', '.join(f'{a} {b}' for a, b in pat.most_common(14)))
