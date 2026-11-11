import gzip, json, sys, collections
from pathlib import Path
def one(d):
    meta=json.loads((d/'meta.json').read_text()); win=meta['result']['winner']
    mp=json.loads((d/meta['mapFile']).resolve().read_text())
    gs={g['id']:g for g in mp['groups']}
    ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    res=collections.Counter()
    for e in ev:
        if e['k']=='capture' and e['r']<=600:
            g=gs[e['g']]; t=e['team']; side=g.get('side')
            rel='own' if side==t else ('enemy' if side==1-t else 'mid')
            res[('W' if t==win else 'L',rel)]+=sum(s[1] for s in e['shares'])
    return res
tot=collections.Counter(); dirs=sorted(p.parent for p in Path(sys.argv[1]).glob('*/meta.json'))
for d in dirs: tot+=one(d)
for k,v in sorted(tot.items()): print(k, round(v/len(dirs),1))
