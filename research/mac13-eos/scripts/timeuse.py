"""Time use per champion type in a round window: walk / camp / hold / recall / spawn / fight / still / dead.
LO=1 HI=200 py timeuse.py EXTRACT_DIR"""
import gzip,json,sys,collections,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
LO=int(os.environ.get('LO','1')); HI=int(os.environ.get('HI','99999'))
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    names={int(c['id']):c['name'] for c in meta['champions']}
    camp=set(); fight=set(); rec=set()
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='camp_attack' and e.get('a') is not None: camp.add((e['r'],e['a']))
        elif e['k'] in ('attack','cast') : fight.add((e['r'],e.get('a')))
    gt={}
    for x in mp['groups']:
        for t in x['tiles']: gt[tuple(t)]=x['id']
    out=collections.Counter(); n=len(R['round'])
    for c in R['champions']:
        cid=int(c['id']); s=mp['spawn'][int(c['team'])]; nm=names[cid]
        for i in range(max(1,LO-1),min(n,HI)):
            r=i+1
            if not c['alive'][i]: out[(nm,'dead')]+=1; continue
            on=s['minX']<=c['x'][i]<=s['maxX'] and s['minY']<=c['y'][i]<=s['maxY']
            moved=(c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1])
            if (r,cid) in camp: k='camp'
            elif (r,cid) in fight: k='fight'
            elif on: k='spawn'
            elif c['chan'][i] not in (0,1): k='channel'
            elif moved: k='walk'
            elif (c['x'][i],c['y'][i]) in gt: k='hold'
            else: k='still'
            out[(nm,k)]+=1
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    T=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(g,dirs,chunksize=8): T.update(r)
    K=['walk','camp','hold','channel','spawn','fight','still','dead']
    tot=collections.Counter()
    for (nm,k),v in T.items(): tot[nm]+=v
    print(f"{'type':14s} "+' '.join(f'{k:>7s}' for k in K))
    all_=collections.Counter()
    for (nm,k),v in T.items(): all_[k]+=v
    S=sum(all_.values()); print(f"{'ALL':14s} "+' '.join(f'{all_[k]/S:7.3f}' for k in K))
    for nm,t in tot.most_common():
        print(f"{nm:14s} "+' '.join(f'{T[(nm,k)]/t:7.3f}' for k in K))
