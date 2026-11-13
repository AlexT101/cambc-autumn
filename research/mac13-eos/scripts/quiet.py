import gzip,json,sys,collections
from pathlib import Path
tot=q=0
by=collections.Counter(); byq=collections.Counter()
for d in list(Path(sys.argv[1]).iterdir())[:200]:
    if not (d/'meta.json').exists(): continue
    m=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    team={int(c['id']):int(c['team']) for c in m['champions']}
    for c in R['champions']:
        t=int(c['team'])
        for i,a in enumerate(c['alive']):
            if not a: continue
            seen=c['sees'][i] if i<len(c['sees']) else []
            en=any(team.get(int(x) if not isinstance(x,list) else int(x[0]),t)!=t for x in seen)
            ph=0 if i<200 else 1 if i<500 else 2
            by[ph]+=1; byq[ph]+= not en
print({k:round(byq[k]/by[k],3) for k in by})
