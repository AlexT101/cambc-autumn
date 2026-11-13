# Occupancy (own/mid/enemy side, by spawn Chebyshev ratio) of alive champions by enemy alive fraction,
# and captures on mid/enemy side by enemy alive fraction at capture time.
import json,gzip,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
idx=json.load(open(ROOT+'/index.json'))
dirs=sorted(set(g['dir'] for g in idx['games']))
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    sp=mp['spawn']; cen=[((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2) for s in sp]
    CH=R['champions']; n=len(R['round'])
    occ=collections.Counter()
    for i in range(0,n,3):
        for team in (0,1):
            es=[c for c in CH if c['team']!=team]
            ealive=sum(c['alive'][i] for c in es)/len(es)
            b='0-49' if ealive<0.5 else '50-99' if ealive<1 else '100'
            for c in CH:
                if c['team']!=team or not c['alive'][i] or c['x'][i] is None: continue
                p=(c['x'][i],c['y'][i]); da=cheb(p,cen[team]); de=cheb(p,cen[1-team])
                s=de/(da+de) if da+de else .5
                z='own' if s>0.6 else 'enemy' if s<0.4 else 'mid'
                occ[(b,z)]+=1; occ[(b,'tot')]+=1
    return occ
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,dirs,chunksize=4) if r]
    T=collections.Counter()
    for r in res: T.update(r)
    for b in ('100','50-99','0-49'):
        t=T[(b,'tot')]; print(b,'enemy alive: samples',t, {z:round(T[(b,z)]/t,3) for z in ('own','mid','enemy')})
