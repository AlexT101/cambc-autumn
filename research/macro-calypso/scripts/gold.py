import gzip, json, sys, collections, statistics
from pathlib import Path
an=Path(sys.argv[1]); g=collections.defaultdict(list)
for d in sorted(p.parent for p in an.glob('*/meta.json'))[:300]:
    meta=json.loads((d/'meta.json').read_text()); names={x['id']:x['name'] for x in meta['champions']}
    R=json.load(gzip.open(d/'rounds.json.gz'))
    for c in R['champions']:
        n=names[c['id']]
        for r in range(100,min(800,len(c['gold'])),50):
            if c['alive'][r]: g[n].append(c['gold'][r])
for n,v in sorted(g.items()):
    v.sort(); print(f'{n:14s} n={len(v)} median={v[len(v)//2]:.0f} p75={v[3*len(v)//4]:.0f} p90={v[9*len(v)//10]:.0f} share>=150={sum(x>=150 for x in v)/len(v):.2f}')
