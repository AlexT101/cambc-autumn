import gzip, json, sys, collections
from pathlib import Path
an=Path(sys.argv[1]); c=collections.Counter(); hp=collections.Counter()
for d in sorted(p.parent for p in an.glob('*/meta.json'))[:300]:
    meta=json.loads((d/'meta.json').read_text()); names={x['id']:x['name'] for x in meta['champions']}
    R=json.load(gzip.open(d/'rounds.json.gz')); idx={x['id']:i for i,x in enumerate(R['champions'])}
    for x in meta['champions']:
        s=x['stats']; n=x['name']
        c[(n,'monsterTaken')]+=s['monsterDamageTaken']; c[(n,'champTaken')]+=s['championDamageTaken']; c[(n,'bodies')]+=1
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='recall_end' and names[e['a']]=='Prism':
            ch=R['champions'][idx[e['a']]]; r=max(0,e['r']-6)
            f=ch['hp'][r]/ch['maxHp'][r]; hp[round(f,1)]+=1; c[('Prism','recalls')]+=1
            c[('Prism','recall_r<=600')]+= e['r']<=600
for n in ['Prism','Vesper Vale','Willow','Cassi','Issac']:
    b=c[(n,'bodies')]; print(n, 'per body: monster taken', round(c[(n,'monsterTaken')]/b), 'champ taken', round(c[(n,'champTaken')]/b))
print('prism recalls/body', c[('Prism','recalls')]/c[('Prism','bodies')], 'hp at recall', sorted(hp.items()))
