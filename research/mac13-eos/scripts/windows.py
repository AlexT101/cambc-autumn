"""Alive-body advantage windows: share of rounds r>=100 where a team has more alive bodies; in those rounds, where
its bodies are (own/mid/enemy share) vs at parity; enemy-side captures in windows."""
import gzip,json,sys,collections,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    sp=[((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2) for s in mp['spawn']]
    ch=R['champions']; n=len(R['round']); out=collections.Counter()
    for i in range(100,n,2):
        al=[sum(1 for c in ch if int(c['team'])==t and c['alive'][i]) for t in (0,1)]
        for t in (0,1):
            st='ahead' if al[t]>al[1-t] else 'behind' if al[t]<al[1-t] else 'par'
            out[(st,'rounds')]+=1
            for c in ch:
                if int(c['team'])!=t or not c['alive'][i]: continue
                p=(c['x'][i],c['y'][i]); d0,d1=cheb(p,sp[t]),cheb(p,sp[1-t]); s=d0/max(1,d0+d1)
                out[(st,'own' if s<0.4 else 'mid' if s<=0.6 else 'enemy')]+=1
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    T=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(g,dirs,chunksize=8): T.update(r)
    tot=sum(T[(s,'rounds')] for s in ('ahead','behind','par'))
    for s in ('ahead','par','behind'):
        b=T[(s,'own')]+T[(s,'mid')]+T[(s,'enemy')]
        print(s,'share of team-rounds',round(T[(s,'rounds')]/tot,3),'bodies own/mid/enemy',round(T[(s,'own')]/b,3),round(T[(s,'mid')]/b,3),round(T[(s,'enemy')]/b,3))
