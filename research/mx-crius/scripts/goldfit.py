"""Logistic fit of team A's win on differences at round T: team wealth (tributed+carried, /100), Prism earned gold (/100),
other bodies' earned gold (/100). Only games where both teams have a Prism."""
import json,gzip,glob,os,sys,math
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]; T=int(sys.argv[2]); CH=json.load(open(R+'/enums.json'))['champions']
def one(p):
    d=os.path.dirname(p); m=json.load(open(p)); typ={c['id']:CH[c['type']] for c in m['champions']}
    RR=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(RR['round'])}
    i=ri.get(T)
    if i is None: return None
    f=[[0,0,0],[0,0,0]]; hasp=[False,False]
    for c in RR['champions']:
        t=c['team']; f[t][0]+=(c['gems'][i] or 0)
        if typ[c['id']]=='Prism': f[t][1]+=c['earned'][i]; hasp[t]=True
        else: f[t][2]+=c['earned'][i]
    for t in (0,1): f[t][0]+=RR['gems'][t][i]
    if not all(hasp): return None
    return ([(f[0][k]-f[1][k])/100 for k in range(3)], 1 if m['result']['winner']==0 else 0)
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json')
    with ProcessPoolExecutor(48) as ex: S=[s for s in ex.map(one,ps,chunksize=8) if s]
    w=[0.0]*4; lr=0.05
    X=[[1.0]+x for x,y in S]; Y=[y for x,y in S]
    for it in range(3000):
        g=[0.0]*4
        for x,y in zip(X,Y):
            z=sum(a*b for a,b in zip(w,x)); pz=1/(1+math.exp(-z))
            for k in range(4): g[k]+=(y-pz)*x[k]
        w=[a+lr*b/len(X) for a,b in zip(w,g)]
    print('T=%d n=%d coef per 100: intercept %.3f wealth %.3f prism_gold %.3f others_gold %.3f'%(T,len(S),*w))
