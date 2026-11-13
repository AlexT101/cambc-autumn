"""Enemy holds within reach: for each capture (payout), the nearest opposing champion (Chebyshev to any group tile)
over the 6 rounds before payout; its gems; and who held."""
import sys, json, gzip, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
        mp = json.loads((d/meta['mapFile']).read_text())
    except Exception: return None
    name = {c['id']: c['name'] for c in meta['champions']}
    gt = {g['id']: g['tiles'] for g in mp['groups']}
    gv = {g['id']: (g['gems'], g['gold']) for g in mp['groups']}
    r0 = R['round'][0]; st = collections.Counter()
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e = json.loads(l)
        if e.get('k') != 'capture': continue
        g, t, r = e['g'], e['team'], e['r']
        best = 99; who = None
        for c in R['champions']:
            if c['team'] == t: continue
            for rr in range(r - 6, r):
                i = rr - r0
                if i < 0 or not c['alive'][i] or c['x'][i] is None: continue
                dd = min(max(abs(c['x'][i]-x), abs(c['y'][i]-y)) for x, y in gt[g])
                if dd < best: best, who = dd, (name[c['id']], c['gems'][i])
        holders = [name[s[0]] for s in e['shares']]
        gems = sum(s[1] for s in e['shares']); gold = sum(s[2] for s in e['shares'])
        b = '<=2' if best <= 2 else '3-4' if best <= 4 else '5-6' if best <= 6 else '7-8' if best <= 8 else '9+'
        st['n'] += 1; st['n_' + b] += 1; st['gems_' + b] += gems; st['gold_' + b] += gold
        if best <= 4: st['near_holder_prism'] += 'Prism' in holders; st['near_by_' + who[0]] += 1
    return st
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    tot = collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if o: tot.update(o)
    n = len(dirs)
    for k in sorted(tot): print(k, round(tot[k]/n, 2))
