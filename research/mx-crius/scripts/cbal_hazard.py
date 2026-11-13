"""Death hazard per contact round (an enemy within R of a living champion) by the Lanchester share
x = P_them / (P_us + P_them), P = sum(output) * sum(health) over the champion and its allies within R
against the enemies within R; output ~ Strength + Focus / 8. Death: killed by a champion in the next round."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
D=sys.argv[1]; R=int(sys.argv[2]) if len(sys.argv)>2 else 6
def one(p):
    d=os.path.dirname(p)
    RR=json.load(gzip.open(d+'/rounds.json.gz')); rounds=RR['round']; n=len(rounds); C=RR['champions']
    kill=set()
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e.get('by',-1)>=0 and not e.get('linked'): kill.add((e['v'],e['r']))
    idx={r:i for i,r in enumerate(rounds)}
    out=[]
    for i in range(1,n-1):
        al=[o for o in C if o['alive'][i] and o['x'][i] is not None]
        for c in al:
            us=[o for o in al if o['team']==c['team'] and max(abs(o['x'][i]-c['x'][i]),abs(o['y'][i]-c['y'][i]))<=R]
            th=[o for o in al if o['team']!=c['team'] and max(abs(o['x'][i]-c['x'][i]),abs(o['y'][i]-c['y'][i]))<=R]
            if not th: continue
            P=lambda s:sum(o['str'][i]+o['foc'][i]/8 for o in s)*sum(o['hp'][i]+o['shield'][i] for o in s)
            pu,pt=P(us),P(th); x=pt/(pu+pt) if pu+pt>0 else .5
            died=(c['id'],rounds[i+1]) in kill or (c['id'],rounds[i]+1) in kill
            out.append((x,died,len(us)-1,len(th)))
    return out
if __name__=='__main__':
    ps=glob.glob(D+'/*/meta.json')[:int(sys.argv[3]) if len(sys.argv)>3 else 600]
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ps,chunksize=4) for x in o]
    print('contact rounds',len(S),'deaths',sum(s[1] for s in S),'hazard %.5f'%(sum(s[1] for s in S)/len(S)))
    b=collections.defaultdict(lambda:[0,0,0.0])
    for x,dd,a,e in S: k=min(9,int(x*10)); b[k][0]+=1; b[k][1]+=dd; b[k][2]+=x
    for k in sorted(b): n,dd,xs=b[k]; xm=xs/n; print('x %.2f n %7d hazard %.5f  /x^2 %.4f  /x %.4f'%(xm,n,dd/n,dd/n/xm/xm,dd/n/xm))
    f=lambda x:min(x,.99)/(1-min(x,.99))**.5
    lam=sum(s[1] for s in S)/sum(f(s[0]) for s in S); print('lambda0 for x/sqrt(1-x): %.5f'%lam)
    b=collections.defaultdict(lambda:[0,0,0.0])
    for x,dd,a,e in S: k=min(9,int(x*10)); b[k][0]+=1; b[k][1]+=dd; b[k][2]+=lam*f(x)
    for k in sorted(b): n,dd,pr=b[k]; print('bin %d measured %.5f predicted %.5f'%(k,dd/n,pr/n))
