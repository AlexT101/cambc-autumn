import gzip, json, sys, collections
from pathlib import Path
an=Path(sys.argv[1]); tot=collections.Counter()
for d in sorted(p.parent for p in an.glob('*/meta.json')):
    meta=json.loads((d/'meta.json').read_text()); names={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    if 'Prism' not in names.values(): continue
    win=meta['result']['winner']
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='capture' and e['r']<=600:
            for cid,gems,gold in e['shares']:
                w='W' if team[cid]==win else 'L'
                tot[(w,'all')]+=gems
                if names[cid]=='Prism': tot[(w,'prism')]+=gems
        if e['k']=='death' and e['r']<=600 and 'by' in e and e.get('by') is not None and e['by'] in names:
            w='W' if team[e['by']]==win else 'L'
            tot[(w,'killgems_all')]+=e.get('gemsTo',0)
            if names[e['by']]=='Prism': tot[(w,'killgems_prism')]+=e.get('gemsTo',0)
for k,v in sorted(tot.items()): print(k,v)
