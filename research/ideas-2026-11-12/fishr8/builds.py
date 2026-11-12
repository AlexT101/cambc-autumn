"""Fish's build order per champion type (live mode): the sequence of items as they first appear (emblem completions,
Greed shown with its shard count), and the most common first-four emblem sequences.  py builds.py EXT ROWS.json"""
import gzip, json, os, sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/mitefit')
from mstats import load
FAM = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospector', 'Hunter', 'Skirmish', 'Greed', 'Collectors']
ST = 'SFH'
ext, rf = sys.argv[1:3]; rows = json.load(open(rf)); idx = json.load(open(ext + '/index.json'))['games']
seqs = collections.defaultdict(collections.Counter); first = collections.defaultdict(list); n = collections.Counter()
for g in idx:
    mid = os.path.basename(g['source'])[:-8]
    if mid not in rows: continue
    fish = 1 if rows[mid]['side'] == 'a' else 0
    meta, R, ev, mp = load(ext, g['dir']); typ = {c['id']: c['name'] for c in meta['champions']}
    for c in R['champions']:
        if c['team'] != fish: continue
        t = typ[c['id']]; n[t] += 1; got = []; prev = {}
        for i, L in enumerate(c['items']):
            cur = dict(zip(L[::2], L[1::2])) if L else {}
            for it, k in cur.items():
                if it % 2 == 1 and k > prev.get(it, 0):
                    f, r = divmod(it, 6); got.append((f'{FAM[f]}-{ST[r // 2]}', i + 1))
            prev = cur
        seqs[t][' '.join(x for x, _ in got[:4])] += 1
        for x, r in got: first[(t, x)].append(r)
for t in sorted(n, key=lambda t: -n[t]):
    print(f'== {t} ({n[t]})')
    for s, k in seqs[t].most_common(4): print(f'   {k:4d} {s}')
    em = sorted(((k[1], v) for k, v in first.items() if k[0] == t), key=lambda x: -len(x[1]))[:8]
    print('   ' + ', '.join(f'{e} {len(v) / n[t]:.2f}@{sorted(v)[len(v) // 2]}' for e, v in em))
