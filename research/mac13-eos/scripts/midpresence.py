"""Per 50-round window r100-500: each team's mean bodies in the middle (and in the enemy half); kill share in the
window by presence difference; and cohesion (mean distance to nearest ally) vs kill share."""
import gzip,json,sys,collections,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    sp=[((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2) for s in mp['spawn']]
    team={int(c['id']):int(c['team']) for c in meta['champions']}
    kills=collections.Counter()
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e.get('by') is not None and e['by'] in team: kills[(e['r']//50,team[e['by']])]+=1
    ch=R['champions']; n=len(R['round']); out=[]
    for w in range(2,10):
        lo,hi=w*50,min(n,w*50+50)
        if hi-lo<20: break
        mid=[0,0]; nn=[0,0]; cnt=[0,0]
        for i in range(lo,hi,2):
            for t in (0,1):
                pos=[(c['x'][i],c['y'][i]) for c in ch if int(c['team'])==t and c['alive'][i]]
                for p in pos:
                    d0,d1=cheb(p,sp[t]),cheb(p,sp[1-t]); s=d0/max(1,d0+d1)
                    mid[t]+= s>=0.4
                    others=[cheb(p,q) for q in pos if q!=p]
                    if others: nn[t]+=min(others); cnt[t]+=1
        k=[kills[(w,0)],kills[(w,1)]]
        out.append((w,mid,[nn[t]/max(1,cnt[t]) for t in (0,1)],k))
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res=[x for r in ex.map(g,dirs,chunksize=8) for x in r]
    # presence advantage vs kill diff
    buck=collections.defaultdict(lambda:[0,0,0])
    coh=collections.defaultdict(lambda:[0,0,0])
    for w,mid,nn,k in res:
        tot=k[0]+k[1]
        if tot==0: continue
        dm=mid[0]-mid[1]; b=('more mid' if dm>len(range(0,50,2))*0.5 else 'less mid' if dm< -len(range(0,50,2))*0.5 else 'even')
        buck[b][0]+=k[0]; buck[b][1]+=tot; buck[b][2]+=1
        dn=nn[0]-nn[1]; c=('tighter' if dn< -1 else 'looser' if dn>1 else 'same')
        coh[c][0]+=k[0]; coh[c][1]+=tot; coh[c][2]+=1
    print('team A kill share by mid presence vs B:',{k:(round(v[0]/v[1],3),v[2]) for k,v in buck.items()})
    print('team A kill share by cohesion (nearest-ally distance) vs B:',{k:(round(v[0]/v[1],3),v[2]) for k,v in coh.items()})
