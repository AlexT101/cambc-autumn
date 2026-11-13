"""Death hazard per 1000 alive rounds by champion type and zone (own <0.4, mid, enemy >0.6 of spawn distance)."""
import gzip,json,sys,collections,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    sp=[((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2) for s in mp['spawn']]
    names={int(c['id']):c['name'] for c in meta['champions']}
    dead={}
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death': dead[(e['v'],e['r'])]=e.get('by') is None
    rounds=collections.Counter(); deaths=collections.Counter()
    for c in R['champions']:
        cid=int(c['id']); t=int(c['team']); nm=names[cid]
        if nm in ('Cassi','Issac'): nm='pair'
        for i,a in enumerate(c['alive']):
            if not a: continue
            p=(c['x'][i],c['y'][i]); d0,d1=cheb(p,sp[t]),cheb(p,sp[1-t]); s=d0/max(1,d0+d1)
            z='own' if s<0.4 else 'mid' if s<=0.6 else 'enemy'
            ph='early' if i<300 else 'late'
            rounds[(nm,z,ph)]+=1
            if (cid,i+2) in dead or (cid,i+1) in dead:
                if (cid,i+2) in dead and i+1<len(c['alive']) and not c['alive'][i+1]: deaths[(nm,z,ph)]+=1
    return rounds,deaths
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    Rn=collections.Counter(); D=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for r,dd in ex.map(g,dirs,chunksize=8): Rn.update(r); D.update(dd)
    types=sorted({k[0] for k in Rn}, key=lambda t:-sum(v for k,v in Rn.items() if k[0]==t))
    for ph in ('early','late'):
        print('==',ph,'(r<300 / r>=300): deaths per 1000 alive rounds, and share of alive time, by zone own/mid/enemy')
        for t in types:
            tot=sum(Rn[(t,z,ph)] for z in ('own','mid','enemy'))
            if tot<20000: continue
            print(f"{t:14s}", ' '.join(f"{z}:{1000*D[(t,z,ph)]/max(1,Rn[(t,z,ph)]):5.2f}({Rn[(t,z,ph)]/tot:.2f})" for z in ('own','mid','enemy')))
