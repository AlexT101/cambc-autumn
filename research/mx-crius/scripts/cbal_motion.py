"""How enemies spread from where they were seen: for a champion's tile p0 at round r (every 10th round, alive) and
each living enemy at Chebyshev distance d from p0, whether that enemy is within 6 of p0 at r+t. Compared with the
uniform-box model (a box growing a tile a round from the enemy's tile, clipped to the map)."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
D=sys.argv[1]; TS=(0,5,10,20,30); K=float(sys.argv[2]) if len(sys.argv)>2 else 0
def one(p):
    d=os.path.dirname(p); m=json.load(open(p)); W,H=m['map']['width'],m['map']['height']
    RR=json.load(gzip.open(d+'/rounds.json.gz')); n=len(RR['round']); C=RR['champions']
    out=[]
    def model(ex,ey,cx,cy,t):
        t=int(min(t,K*t**.5)) if K else t
        bx0,bx1,by0,by1=max(0,ex-t),min(W-1,ex+t),max(0,ey-t),min(H-1,ey+t)
        sx0,sx1,sy0,sy1=max(0,cx-6),min(W-1,cx+6),max(0,cy-6),min(H-1,cy+6)
        ix=min(bx1,sx1)-max(bx0,sx0)+1; iy=min(by1,sy1)-max(by0,sy0)+1
        return 0 if ix<=0 or iy<=0 else ix*iy/((bx1-bx0+1)*(by1-by0+1))
    for i in range(20,n-31,10):
        for c in C:
            if not c['alive'][i] or c['x'][i] is None: continue
            cx,cy=c['x'][i],c['y'][i]
            for e in C:
                if e['team']==c['team'] or not e['alive'][i] or e['x'][i] is None: continue
                dd=max(abs(e['x'][i]-cx),abs(e['y'][i]-cy))
                if dd>16: continue
                for t in TS:
                    j=i+t
                    if not e['alive'][j] or e['x'][j] is None: hit=0
                    else: hit=max(abs(e['x'][j]-cx),abs(e['y'][j]-cy))<=6
                    out.append((dd,t,hit,model(e['x'][i],e['y'][i],cx,cy,t)))
    return out
if __name__=='__main__':
    ps=glob.glob(D+'/*/meta.json')[:150]
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ps,chunksize=2) for x in o]
    b=collections.defaultdict(lambda:[0,0,0.0])
    for dd,t,h,mo in S: k=(min(dd//2*2,16),t); b[k][0]+=1; b[k][1]+=h; b[k][2]+=mo
    for dd in range(0,17,2):
        print('d %2d-%2d '%(dd,dd+1)+'  '.join('t%d %.2f/%.2f'%(t,b[(dd,t)][1]/max(1,b[(dd,t)][0]),b[(dd,t)][2]/max(1,b[(dd,t)][0])) for t in TS))
    err=sum(b[k][0]*(b[k][1]/b[k][0]-b[k][2]/b[k][0])**2 for k in b if b[k][0])/sum(b[k][0] for k in b)
    print('K',K,'weighted sq err %.5f'%err)
