import json,gzip,glob,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; RR=int(sys.argv[2])
en=json.load(open(ROOT+'/enums.json'))['champions']
def one(d):
    meta=json.load(open(d+'/meta.json'))
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    if len(R['round'])<RR+1: return None
    i=RR-1
    out=[]
    for team in (0,1):
        tot=R['gems'][team][i]; p=0; foc=0
        for ci,c in enumerate(R['champions']):
            if c['team']!=team: continue
            g=c['gems'][i] or 0; tot+=g
            if en[meta['champions'][ci]['type']]=='Prism': p=g; foc=c['foc'][i]
        out.append((tot,p,foc))
    if out[0][2]==0 or out[1][2]==0: return None
    return out, meta['result']['winner']
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,ds,chunksize=8) if r]
    # pairs with near-equal totals
    B=collections.defaultdict(lambda:[0,0])
    for (a,b),w in res:
        if min(a[0],b[0])<50: continue
        if abs(a[0]-b[0])/max(a[0],b[0])>0.1: continue
        for me,ot,won in ((a,b,w==0),(b,a,w==1)):
            ds_=me[1]/me[0]-ot[1]/ot[0]
            k='share+0.1' if ds_>0.1 else 'share-0.1' if ds_<-0.1 else 'share~'
            B[k][0]+=won; B[k][1]+=1
    print('r',RR,'equal totals (+-10%):',{k:(f"{v[0]/v[1]:.3f}",v[1]) for k,v in B.items()})
