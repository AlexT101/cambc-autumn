"""Before each Prism death: how long since its first retreat turn in the chain of retreats leading to it, and how many
times it went back to work in between (debug builds' D lines): python3 yoyo.py EXTROOT/TAG
A chain: retreat turns (R) with gaps of at most GAP rounds between them."""
import collections, gzip, json, os, sys, zipfile
from multiprocessing import Pool
ROOT = '/home/ubuntu/cambc-autumn'
GAP = 8


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    pr = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; D = {}
    for line in out.replace('\x00', '').splitlines():
        v = line.split()
        if len(v) >= 4 and v[0] == 'D' and v[2] == str(p):
            try: D[int(v[1])] = v[3]
            except ValueError: pass
    res = []
    for x in ev:
        if x['k'] != 'death' or x['v'] != p or x.get('by') is None: continue
        r = x['r']; q = r; first = None; back = 0; work = collections.Counter(); last_r = None; inwork = False
        gap = 0
        while q > 0 and gap <= GAP:
            a = D.get(q, '.')
            if a == 'R':
                if inwork and first is not None: back += 1
                first = q; gap = 0; inwork = False
            else:
                gap += 1
                if first is not None and a not in ('.', '-'): inwork = True; work[a] += 1
            q -= 1
        res.append((r - first if first else -1, back, dict(work), x.get('gems', 0)))
    return res


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    n = len(R)
    print(n, 'Prism deaths to champions')
    b = lambda x: 'no retreat' if x < 0 else '<4' if x < 4 else '<8' if x < 8 else '<16' if x < 16 else '<32' if x < 32 else '32+'
    c = collections.Counter(b(r[0]) for r in R)
    print('rounds from the first retreat turn of the chain to the death:', ', '.join(f'{k} {100 * c[k] / n:.0f}%' for k in ('no retreat', '<4', '<8', '<16', '<32', '32+')))
    c = collections.Counter(min(r[1], 4) for r in R)
    print('times it went back to other work inside the chain:', ', '.join(f'{k}{"+" if k == 4 else ""}: {100 * c[k] / n:.0f}%' for k in sorted(c)))
    w = collections.Counter()
    for r in R: w.update(r[2])
    tot = sum(w.values())
    print('the work turns inside chains:', ', '.join(f'{a} {100 * v / tot:.0f}%' for a, v in w.most_common(8)))
    L = [r for r in R if r[0] >= 16]
    print(f'chains of 16+ rounds: {len(L)} ({100 * len(L) / n:.0f}%), mean returns to work {sum(r[1] for r in L) / max(1, len(L)):.1f}')
