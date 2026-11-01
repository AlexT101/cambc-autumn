import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
# one-pursuer chases: our retreater vs the single pursuer; record hp/str of both and who dealt damage
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; mp=mapj(m)
    F=[spawn_field(mp,0),spawn_field(mp,1)]; N=len(R['round']); out=[]
    NM={c['id']:c['name'] for c in m['champions']}; CH=R['champions']
    HIT=[]
    for e in events(d):
        if e['k'] in('attack','cast'):
            for v,a in (e.get('dmg') or []): HIT.append((e['r'],e['a'],v,a,e.get('ab'),e.get('stun')))
    for c in CH:
        t=c['team']; side='us' if t==us else 'them'; f=F[t]
        P=lambda i,c=c:(c['x'][i],c['y'][i])
        i=1
        while i<N-6:
            if not (c['alive'][i] and c['alive'][i-1]): i+=1; continue
            en=[e for e in CH if e['team']!=t and e['alive'][i] and cheb((e['x'][i],e['y'][i]),P(i))<=6]
            d0=f.get(P(i))
            if not en or not d0: i+=1; continue
            ok=all(c['alive'][i+k] and f.get(P(i+k),99)<f.get(P(i+k-1),99) for k in range(1,5))
            if ok and not f.get(P(i),99)<f.get(P(i-1),99):
                purs=[e for e in en if all(e['alive'][i+k] and cheb((e['x'][i+k],e['y'][i+k]),P(i+k))<=3 for k in (2,4))]
                if len(purs)==1:
                    e=purs[0]
                    others=[x for x in CH if x['team']!=t and x is not e and x['alive'][i] and cheb((x['x'][i],x['y'][i]),P(i))<=8]
                    allies=[x for x in CH if x['team']==t and x is not c and x['alive'][i] and cheb((x['x'][i],x['y'][i]),P(i))<=8]
                    res='alive'
                    for j in range(i,min(N,i+40)):
                        if not c['alive'][j]: res='died'; break
                        if f.get(P(j),99)==0: res='spawn'; break
                    back=sum(a for (rr,aa,v,a,ab,st) in HIT if i<=rr<=i+10 and aa==c['id'] and v==e['id'])
                    took=sum(a for (rr,aa,v,a,ab,st) in HIT if i<=rr<=i+10 and v==c['id'])
                    peel=sum(a for (rr,aa,v,a,ab,st) in HIT if i<=rr<=i+10 and v==e['id'] and aa in {x['id'] for x in allies})
                    pdied=any(not e['alive'][j] for j in range(i,min(N,i+15)))
                    jd=next((j for j in range(i,min(N,i+15)) if not e['alive'][j]),None)
                    late=len([x for x in CH if x['team']==t and x is not c and x['alive'][min(N-1,i+6)] and cheb((x['x'][min(N-1,i+6)],x['y'][min(N-1,i+6)]),(e['x'][min(N-1,i+6)],e['y'][min(N-1,i+6)]))<=6]) if e['alive'][min(N-1,i+6)] else -1
                    sd_e=F[e['team']].get((e['x'][i],e['y'][i]))
                    stunned=sum(1 for (rr,aa,v,a,ab,st) in HIT if i<=rr<=i+10 and st and c['id'] in st)
                    out.append(dict(side=side,opp=r['opp'],me=NM[c['id']],mh=c['hp'][i],mm=c['maxHp'][i],ms=c['str'][i],pu=NM[e['id']],ph=e['hp'][i],pm=e['maxHp'][i],ps=e['str'][i],
                        others=len(others),peel=peel,late=late,sd_e=sd_e,pdied=pdied,allies=len(allies),res=res,back=back,took=took,stunned=stunned,src=r['source'],r=R['round'][i],d0=d0))
                i+=5; continue
            i+=1
    return out
def _x(): pass
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,games()) for x in o]
    json.dump(res,open(sys.argv[1]+'/chase1.json','w'))
    for side in ('us','them'):
        X=[x for x in res if x['side']==side]
        # perspective: pursuer team = other side
        print('pursuer team', 'them' if side=='us' else 'us')
        for lab,fn in [('allies of retreater within6 of pursuer at +6 =0',lambda x:x['late']==0),('=1',lambda x:x['late']==1),('>=2',lambda x:x['late']>=2)]:
            Y=[x for x in X if fn(x)]
            print('   %-48s n=%4d pursuer died %.2f retreater died %.2f'%(lab,len(Y),sum(x['pdied'] for x in Y)/len(Y),sum(x['res']=='died' for x in Y)/len(Y)))
        import statistics as st
        print('   pursuer spawn-dist at start (own spawn) median', st.median([x['sd_e'] for x in X if x['sd_e'] is not None]))
