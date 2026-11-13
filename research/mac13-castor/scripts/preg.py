import json,gzip,glob,collections,sys,os
import numpy as np
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
RS=[150,200,300,400,500]
def one(d):
    meta=json.load(open(d+'/meta.json'))
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    out={}
    for RR in RS:
        if len(R['round'])<RR+1: continue
        i=RR-1; v=[]
        for team in (0,1):
            trib=R['gems'][team][i]; car=0; p=0
            for ci,c in enumerate(R['champions']):
                if c['team']!=team: continue
                g=c['gems'][i] or 0
                if en[meta['champions'][ci]['type']]=='Prism': p=g
                else: car+=g
            v.append((trib,car,p))
        out[RR]=v
    return out, meta['result']['winner'], any(en[c['type']]=='Prism' for c in meta['champions'] if c['team']==0) and any(en[c['type']]=='Prism' for c in meta['champions'] if c['team']==1)
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: res=list(ex.map(one,ds,chunksize=8))
    for RR in RS:
        X=[];y=[]
        for o,w,both in res:
            if not both or RR not in o: continue
            a,b=o[RR]
            X.append([a[0]-b[0],a[1]-b[1],a[2]-b[2]]); y.append(1 if w==0 else 0)
            X.append([b[0]-a[0],b[1]-a[1],b[2]-a[2]]); y.append(1-y[-1])
        X=np.array(X,float)/100; y=np.array(y)
        # logistic regression no intercept via Newton
        w=np.zeros(3)
        for _ in range(50):
            p=1/(1+np.exp(-X@w)); g=X.T@(y-p); H=-(X.T*(p*(1-p)))@X
            w-=np.linalg.solve(H,g)
        se=np.sqrt(np.diag(np.linalg.inv(-H)))
        print(RR,len(y)//2,'coef per 100 gems: tributed %.2f±%.2f other-carried %.2f±%.2f prism-carried %.2f±%.2f'%(w[0],se[0],w[1],se[1],w[2],se[2]))
