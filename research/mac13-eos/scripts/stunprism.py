"""Turns where one of our unit-stunners (Cassi slot1, Tavi slot1, Ren slot0, Prism slot0) starts its turn alive,
stun ready, with the visible enemy Prism within 4: how often it casts at the Prism's tile that turn."""
import gzip,json,sys,collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
SLOT={'Cassi':1,'Tavi':1,'Ren':0,'Prism':0}
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    names={int(c['id']):c['name'] for c in meta['champions']}
    casts=collections.defaultdict(list)
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='cast': casts[(e['r'],e['a'])].append((e['slot'],tuple(e.get('to') or [])))
    ch={int(c['id']):c for c in R['champions']}
    out=collections.Counter()
    prisms=[k for k,v in names.items() if v=='Prism']
    for cid,c in ch.items():
        nm=names[cid]
        if nm not in SLOT: continue
        s=SLOT[nm]; cd=c['cd%d'%s]
        for P in prisms:
            if int(ch[P]['team'])==int(c['team']): continue
            p=ch[P]
            for i in range(1,len(c['alive'])):
                if not c['alive'][i] or not p['alive'][i-1] or cd[i-1]!=0: continue
                if c['x'][i-1] is None or p['x'][i-1] is None: continue
                if P not in [x if not isinstance(x,list) else x[0] for x in c['sees'][i-1]]: continue
                dd=max(abs(c['x'][i-1]-p['x'][i-1]),abs(c['y'][i-1]-p['y'][i-1]))
                if dd>4: continue
                cs=casts.get((i+1,cid),[])
                px=p['x'][i] if p['x'][i] is not None else p['x'][i-1]; py=p['y'][i] if p['y'][i] is not None else p['y'][i-1]; hit=any(sl==s and to and max(abs(to[0]-px),abs(to[1]-py))<=1 for sl,to in cs)
                any_s=any(sl==s for sl,to in cs)
                out[(nm,'opp')]+=1; out[(nm,'stun_prism')]+=hit; out[(nm,'cast_slot')]+=any_s
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()][:400]
    T=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(g,dirs,chunksize=8): T.update(r)
    for nm in SLOT:
        o=T[(nm,'opp')]
        if o: print(nm,'opportunities/game',round(o/len(dirs),2),'stunned the Prism',round(T[(nm,'stun_prism')]/o,2),'cast that slot at all',round(T[(nm,'cast_slot')]/o,2))
