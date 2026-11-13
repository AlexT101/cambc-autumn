"""For champion kills: consecutive rounds (ending the round before death) the victim saw its killer, and the victim's
distance to the killer when first seen in that run; the victim's HP fraction then."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]; CH=json.load(open(R+'/enums.json'))['champions']
def one(p):
    d=os.path.dirname(p); m=json.load(open(p))
    RR=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(RR['round'])}; ci={c['id']:c for c in RR['champions']}
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('by') is None or e.get('linked'): continue
        v,k=e['v'],e['by']; i=ri.get(e['r']-1)
        if i is None: continue
        run=0; j=i
        while j>=0 and k in (ci[v]['sees'][j] or []): run+=1; j-=1
        if run==0: out.append((0,None,None)); continue
        j+=1; V=ci[v]; K=ci[k]
        dd=max(abs(V['x'][j]-K['x'][j]),abs(V['y'][j]-K['y'][j])) if V['x'][j] is not None and K['x'][j] is not None else None
        out.append((run,dd,V['hp'][j]/V['maxHp'][j]))
    return out
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json')
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ps,chunksize=8) for x in o]
    c=collections.Counter(min(s[0],10) for s in S); n=len(S)
    print('rounds victim saw killer before death:',' '.join('%d:%.0f%%'%(k,100*v/n) for k,v in sorted(c.items())))
    for lo,hi in ((1,2),(3,5),(6,99)):
        xs=[s for s in S if lo<=s[0]<=hi and s[1] is not None]
        if xs: print(' run %d-%d: first-seen distance median %d, hp>=0.9 at first sight %.0f%%'%(lo,hi,sorted(x[1] for x in xs)[len(xs)//2],100*sum(1 for x in xs if x[2]>=0.9)/len(xs)))
