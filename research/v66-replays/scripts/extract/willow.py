import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; mp=mapj(m)
    W=[c for c in m['champions'] if c['name']=='Willow']
    if not W: return []
    heals=defaultdict(set)
    for e in events(d):
        if e['k']=='cast' and e.get('ab')=='Heal': heals[e['a']].add(e['r'])
    CH={c['id']:c for c in R['champions']}; out=[]
    for w in W:
        c=CH[w['id']]; t=w['team']; sp=mp['spawn'][t]
        for i in range(1,len(R['round'])-1):
            if not c['alive'][i] or c['cd0'][i]!=0: continue
            p=(c['x'][i],c['y'][i])
            amt=3*c['foc'][i]
            best=0
            for a in R['champions']:
                if a['team']!=t or a['id']==w['id'] or not a['alive'][i]: continue
                q=(a['x'][i],a['y'][i])
                if sp['minX']<=q[0]<=sp['maxX'] and sp['minY']<=q[1]<=sp['maxY']: continue
                if cheb(p,q)<=4: best=max(best,min(amt,a['maxHp'][i]-a['hp'][i])/amt)
            if best<=0: continue
            out.append(('us' if t==us else 'them',round(min(best,1),1),R['round'][i+1] in heals[w['id']]))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,games()) for x in o]
    for s in ('us','them'):
        X=[x for x in res if x[0]==s]
        print(s,'rounds heal ready & hurt ally within 4:',len(X))
        for b in (0.1,0.3,0.5,0.7,1.0):
            Y=[x for x in X if abs(x[1]-b)<0.11]
            if Y: print('   gain/amount ~%.1f n=%5d healed next round %.2f'%(b,len(Y),sum(x[2] for x in Y)/len(Y)))
