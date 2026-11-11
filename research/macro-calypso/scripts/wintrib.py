import gzip, json, sys, collections
from pathlib import Path
an=Path(sys.argv[1]); c=collections.Counter(); lens=[]
for d in sorted(p.parent for p in an.glob('*/meta.json')):
    meta=json.loads((d/'meta.json').read_text()); win=meta['result']['winner']; team={x['id']:x['team'] for x in meta['champions']}
    names={x['id']:x['name'] for x in meta['champions']}
    starts={}; ended=False
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='tribute_start':
            starts[e['a']]=e
        if e['k']=='tribute_end' and e['gems']>=200:
            c['end200']+=1; c['end200_won']+= team[e['a']]==win
            s=starts.get(e['a']); 
            if s: lens.append(e['r']-s['r'])
        if e['k']=='tribute_cancel':
            s=starts.get(e['a'])
    # game end mode
    c['games']+=1
print(c); lens.sort(); print('channel rounds for 200+ completed', lens[len(lens)//4], lens[len(lens)//2], lens[3*len(lens)//4], len(lens))
