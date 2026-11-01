import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; mp=mapj(m)
    F=[spawn_field(mp,0),spawn_field(mp,1)]
    N=len(R['round']); out=[]
    NM={c['id']:c['name'] for c in m['champions']}
    HIT=defaultdict(list)
    for e in events(d):
        if e['k'] in ('attack','cast'):
            for v,a in (e.get('dmg') or []): HIT[v].append((e['r'],v,a))
        elif e['k']=='camp_attack' and e.get('tgt') is not None: pass
    CH=R['champions']
    for c in CH:
        t=c['team']; side='us' if t==us else 'them'; f=F[t]
        def P(i): return (c['x'][i],c['y'][i])
        i=1
        while i<N-6:
            if not (c['alive'][i] and c['alive'][i-1]): i+=1; continue
            # enemy within 6 at i
            en=[e for e in CH if e['team']!=t and e['alive'][i] and cheb((e['x'][i],e['y'][i]),P(i))<=6]
            if not en: i+=1; continue
            d0=f.get(P(i)); 
            if d0 is None or d0==0: i+=1; continue
            # sustained retreat: spawn distance strictly decreasing for 4 rounds (or reached spawn), was not decreasing previous round
            ok=all(c['alive'][i+k] and f.get(P(i+k),99)<f.get(P(i+k-1),99) for k in range(1,5))
            prev_dec = f.get(P(i),99)<f.get(P(i-1),99)
            if ok and not prev_dec:
                hpf=c['hp'][i]/c['maxHp'][i]
                res='alive'
                for j in range(i,min(N,i+40)):
                    if not c['alive'][j]: res='died'; break
                    if f.get(P(j),99)==0: res='spawn'; break
                purs=[e for e in en if all(e['alive'][i+k] and cheb((e['x'][i+k],e['y'][i+k]),P(i+k))<=3 for k in (2,4))]
                pn=[NM[e['id']] for e in purs]
                dmg=sum(a for (rr,v,a) in HIT[c['id']] if i<rr<=i+8)
                out.append((side,r['opp'],round(hpf,1),d0,res,len(en),pn,dmg,c['maxHp'][i],NM[c['id']]))
                i+=5; continue
            i+=1
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,games()) for x in o]
    json.dump(res,open(sys.argv[1]+'/retreat.json','w'))
    import statistics as st
    for side in ('us','them'):
        X=[x for x in res if x[0]==side]
        c=Counter(min(len(x[6]),3) for x in X); print(side,'pursuers dist', {k:'%.2f'%(v/len(X)) for k,v in sorted(c.items())})
        for k in range(4):
            Y=[x for x in X if min(len(x[6]),3)==k]; 
            if Y: print('   pursuers',k,'n',len(Y),'died %.2f'%(sum(x[4]=='died' for x in Y)/len(Y)),'dmg/maxhp %.2f'%(sum(x[7]/x[8] for x in Y)/len(Y)))
        pc=Counter(n for x in X for n in x[6]); print('   pursuer types',pc.most_common(8))
        vc=Counter(x[9] for x in X if x[4]=='died'); vt=Counter(x[9] for x in X); print('   retreat death rate by type',{k:'%.2f/%d'%(vc[k]/vt[k],vt[k]) for k in vt if vt[k]>100})
