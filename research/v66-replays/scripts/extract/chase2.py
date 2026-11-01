import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; mp=mapj(m); NM={c['id']:c['name'] for c in m['champions']}
    F=[spawn_field(mp,0),spawn_field(mp,1)]; N=len(R['round']); CH=R['champions']
    EV=defaultdict(list)
    for e in events(d):
        if 'a' in e: EV[e['a']].append(e)
    hitsOn=defaultdict(list)
    for a,L in EV.items():
        for e in L:
            if e['k'] in('attack','cast'):
                for v,x in (e.get('dmg') or []): hitsOn[v].append((e['r'],a,x,e['k'],e.get('ab')))
                for v in (e.get('stun') or []): hitsOn[v].append((e['r'],a,0,'stun',None))
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
                    W=range(i,i+9)
                    mine=[e for e in EV[c['id']] if e['r'] in W]
                    o=Counter()
                    for e in mine:
                        if e['k']=='cast': o['cast_'+str(e.get('ab'))]+=1
                        if e['k']=='attack' and any(v in {p['id'] for p in purs} for v,x in (e.get('dmg') or [])): o['atk_back']+=1
                        if e['k']=='move': o['moves']+=1
                        if e['k']=='recall_start': o['recall']+=1
                    for (rr,a,x,k,ab) in hitsOn[c['id']]:
                        if rr in W:
                            if k=='stun': o['stunned']+=1
                            else: o['hits_taken']+=1; o['dmg_taken']+=x
                    alive_rounds=sum(1 for j in W if c['alive'][j])
                    o['alive_rounds']=alive_rounds
                    died=any(not c['alive'][j] for j in range(i,min(N,i+30)))
                    out.append(('us' if t==us else 'them',NM[c['id']],died,dict(o),c['hp'][i]/c['maxHp'][i]))
                i+=5; continue
            i+=1
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,games()) for x in o]
    json.dump(res,open(sys.argv[1]+'/chase2.json','w'))
    for s in ('us','them'):
        X=[x for x in res if x[0]==s]
        keys=sorted({k for x in X for k in x[3]})
        print(s,len(X))
        for k in keys:
            print('   %-22s per chase %.2f'%(k,sum(x[3].get(k,0) for x in X)/len(X)))
    # by retreater type for the frequent ones
    for nm in ('Heart of Ruin','Marcella','Vendetta','Prism','Issac','Cassi'):
        for s in ('us','them'):
            X=[x for x in res if x[0]==s and x[1]==nm]
            if len(X)<50: continue
            print(nm,s,len(X),'died %.2f'%(sum(x[2] for x in X)/len(X)),' '.join('%s %.2f'%(k,sum(x[3].get(k,0) for x in X)/len(X)) for k in ('cast_Dash','cast_Shield','atk_back','hits_taken','stunned','moves','recall','cast_Attack reset','cast_Damage')))
