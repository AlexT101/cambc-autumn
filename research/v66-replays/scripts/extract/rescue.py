import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
# chase episodes (retreater + pursuers within 3 at +2,+4). For each healthy ally (>=70% hp, alive, not the retreater) within 10 of the pursuer at start:
# did it close distance to the nearest pursuer over the next 4 rounds, and did it damage a pursuer within 8 rounds?
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; mp=mapj(m)
    F=[spawn_field(mp,0),spawn_field(mp,1)]; N=len(R['round']); CH=R['champions']
    HIT=defaultdict(set)
    for e in events(d):
        if e['k'] in('attack','cast'):
            for v,a in (e.get('dmg') or []): HIT[(e['a'],v)].add(e['r'])
    out=[]
    for c in CH:
        t=c['team']; f=F[t]; P=lambda i,c=c:(c['x'][i],c['y'][i])
        i=1
        while i<N-9:
            if not(c['alive'][i] and c['alive'][i-1]) or not f.get(P(i)): i+=1; continue
            ok=all(c['alive'][i+k] and f.get(P(i+k),99)<f.get(P(i+k-1),99) for k in range(1,5))
            if ok and not f.get(P(i),99)<f.get(P(i-1),99):
                purs=[e for e in CH if e['team']!=t and all(e['alive'][i+k] and cheb((e['x'][i+k],e['y'][i+k]),P(i+k))<=3 for k in (0,2,4))]
                if purs:
                    for a in CH:
                        if a['team']!=t or a is c or not a['alive'][i] or a['hp'][i]<0.7*a['maxHp'][i]: continue
                        dp=lambda j,a=a:min(cheb((a['x'][j],a['y'][j]),(e['x'][j],e['y'][j])) for e in purs if e['alive'][j])
                        d0=dp(i)
                        if d0>10 or d0<=1: continue
                        if not all(a['alive'][i+k] for k in range(5)): continue
                        closed=dp(i+4)<d0
                        hit=any(any(i<=x<=i+8 for x in HIT[(a['id'],e['id'])]) for e in purs)
                        res='died' if any(not c['alive'][j] for j in range(i,min(N,i+30))) else 'ok'
                        out.append(('us' if t==us else 'them',d0,closed,hit,res,a['hp'][i]/a['maxHp'][i],f.get((a['x'][i],a['y'][i]))))
                i+=5; continue
            i+=1
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,games()) for x in o]
    for s in ('us','them'):
        X=[x for x in res if x[0]==s]
        print(s,'healthy-ally observations',len(X),'closed in 4r %.2f'%(sum(x[2] for x in X)/len(X)),'hit pursuer in 8r %.2f'%(sum(x[3] for x in X)/len(X)))
        for lo,hi in ((2,4),(5,7),(8,10)):
            Y=[x for x in X if lo<=x[1]<=hi]; print('   dist %d-%d n=%d closed %.2f hit %.2f'%(lo,hi,len(Y),sum(x[2] for x in Y)/len(Y),sum(x[3] for x in Y)/len(Y)))
        for cl in (True,False):
            Y=[x for x in X if x[3]==cl]; print('   ally hit pursuer=%s: retreater died %.2f (n=%d)'%(cl,sum(x[4]=='died' for x in Y)/len(Y),len(Y)))
