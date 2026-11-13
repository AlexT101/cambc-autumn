import json,gzip,glob,collections,sys,os
import numpy as np
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
RS=[150,300,500]
def one(d):
    meta=json.load(open(d+'/meta.json'))
    if any(en[c['type']]=='Prism' for c in meta['champions']): return None
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    out={}
    for RR in RS:
        if len(R['round'])<RR+1: continue
        i=RR-1; v=[]
        for team in (0,1):
            trib=R['gems'][team][i]; car=0; gold=0; alive=0
            for c in R['champions']:
                if c['team']!=team: continue
                car+=c['gems'][i] or 0; gold+=c['earned'][i]; alive+=c['alive'][i]
            v.append((trib,car,gold/10,alive*100))
        out[RR]=v
    return out, meta['result']['winner']
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,ds,chunksize=8) if r]
    print('noprism games',len(res))
    for RR in RS:
        X=[];y=[]
        for o,w in res:
            if RR not in o: continue
            a,b=o[RR]; dv=[a[k]-b[k] for k in range(4)]
            X.append(dv); y.append(1 if w==0 else 0); X.append([-x for x in dv]); y.append(1-y[-1])
        X=np.array(X,float)/100; y=np.array(y); w=np.zeros(4)
        for _ in range(50):
            p=1/(1+np.exp(-X@w)); g=X.T@(y-p); H=-(X.T*(p*(1-p)))@X; w-=np.linalg.solve(H-1e-6*np.eye(4),g)
        se=np.sqrt(np.diag(np.linalg.inv(-H)))
        print(RR,len(y)//2,'per 100: tributed %.2f±%.2f carried %.2f±%.2f gold(x10) %.2f±%.2f alive-bodies %.2f±%.2f'%(w[0],se[0],w[1],se[1],w[2],se[2],w[3],se[3]))
