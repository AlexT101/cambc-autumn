import gzip, json, sys, collections
from pathlib import Path
an=Path(sys.argv[1]); c=collections.Counter()
for d in sorted(p.parent for p in an.glob('*/meta.json')):
    meta=json.loads((d/'meta.json').read_text()); names={x['id']:x['name'] for x in meta['champions']}; team={x['id']:x['team'] for x in meta['champions']}
    win=meta['result']['winner']
    if list(names.values()).count('Prism')<2: continue
    c['games']+=1
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and names.get(e['v'])=='Prism' and e['gems']>=50:
            c['first big prism death']+=1; c['victim team won']+= team[e['v']]==win
            c['r<400']+= e['r']<400
            break
print(c)
