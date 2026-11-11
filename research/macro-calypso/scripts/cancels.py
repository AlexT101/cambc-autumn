import gzip, json, sys, collections
from pathlib import Path
an=Path(sys.argv[1]); c=collections.Counter()
for d in sorted(p.parent for p in an.glob('*/meta.json')):
    meta=json.loads((d/'meta.json').read_text()); win=meta['result']['winner']; team={x['id']:x['team'] for x in meta['champions']}
    ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    deaths=[(e['r'],e['v']) for e in ev if e['k']=='death']
    for e in ev:
        if e['k']=='tribute_cancel' and e['gems']>=200:
            cause=e.get('cause'); c[cause]+=1
            died=any(v==e['a'] and e['r']<=r<=e['r']+8 for r,v in deaths)
            c[(cause,'died8')]+=died
            c[(cause,'won')]+= team[e['a']]==win
print(sorted(c.items(), key=str))
