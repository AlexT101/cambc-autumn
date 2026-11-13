"""Ability use: casts per 8 alive rounds by type and slot (1.0 = every cooldown), and the share of rounds a slot sat
ready (cd 0) while the champion attacked a camp without casting it."""
import gzip,json,sys,collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    names={int(c['id']):c['name'] for c in meta['champions']}
    team={int(c['id']):int(c['team']) for c in meta['champions']}
    casts=collections.Counter(); campatk=set(); castr=set()
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='cast': casts[(e['a'],e['slot'],e.get('ab'))]+=1; castr.add((e['r'],e['a'],e['slot']))
        if e['k']=='attack' and e.get('camp') is not None: campatk.add((e['r'],e['a']))
    out=collections.Counter(); ab={}
    for c in R['champions']:
        cid=int(c['id']); nm=names[cid]
        alive=sum(c['alive'])
        out[(nm,'alive')]+=alive
        for (a,s,n),v in casts.items():
            if a==cid: out[(nm,s)]+=v; ab[(nm,s)]=n
        for s in (0,1):
            cd=c['cd%d'%s]
            for i in range(1,len(cd)):
                if c['alive'][i] and cd[i-1]==0 and (i+1,cid) in campatk:
                    out[(nm,s,'readyatk')]+=1
                    if (i+1,cid,s) not in castr:
                        out[(nm,s,'unused')]+=1
                        seen=c['sees'][i] if i<len(c['sees']) else []
                        en=any(team.get(x if not isinstance(x,list) else x[0])!=team[cid] for x in seen)
                        if not en: out[(nm,s,'unused_quiet')]+=1
    return out,ab
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()][:400]
    T=collections.Counter(); AB={}
    with ProcessPoolExecutor(32) as ex:
        for r,ab in ex.map(g,dirs,chunksize=8): T.update(r); AB.update(ab)
    for nm in sorted({k[0] for k in T}):
        a=T[(nm,'alive')]
        if a<50000: continue
        print(f"{nm:14s}", ' | '.join(f"s{s} {AB.get((nm,s),'?')}: {8*T[(nm,s)]/a:.2f}/cd, ready while hitting camps {T[(nm,s,'readyatk')]/a:.3f} of alive, unused {T[(nm,s,'unused')]/max(1,T[(nm,s,'readyatk')]):.2f} quiet-unused {T[(nm,s,'unused_quiet')]/max(1,T[(nm,s,'readyatk')]):.2f}" for s in (0,1)))
