import gzip, json, sys, collections
from pathlib import Path
an=Path(sys.argv[1]); c=collections.Counter()
for d in sorted(p.parent for p in an.glob('*/meta.json')):
    meta=json.loads((d/'meta.json').read_text()); names={x['id']:x['name'] for x in meta['champions']}
    R=json.load(gzip.open(d/'rounds.json.gz')); idx={x['id']:i for i,x in enumerate(R['champions'])}
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and names.get(e['v'])=='Prism' and e.get('by') in names and names[e['by']]=='Prism' and e['gems']>=100:
            r=max(0,e['r']-1); kb=R['champions'][idx[e['by']]]['gems'][r]
            c['victim smaller' if e['gems']<kb else 'victim bigger']+=1
print(c)
