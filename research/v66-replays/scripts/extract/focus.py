import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); ev=events(d); us=r['us']
    team={c['id']:c['team'] for c in m['champions']}; name={c['id']:c['name'] for c in m['champions']}
    # window segmentation per 10-round buckets of hits within 8 tiles: reuse simple time-gap clustering per game
    hits=[]; deaths=[]
    for e in ev:
        if e['k'] in('attack','cast'):
            for v,a in (e.get('dmg') or []):
                if v in team and team[v]!=team[e['a']]: hits.append((e['r'],e['a'],v,a,e['k'],e.get('ab')))
        if e['k']=='death' and e.get('linked') is None and e.get('by') is not None: deaths.append(e)
    # windows: hits clustered by time gap>6
    wins=[]; cur=[]
    for h in hits:
        if cur and h[0]-cur[-1][0]>6: wins.append(cur); cur=[]
        cur.append(h)
    if cur: wins.append(cur)
    out=[]
    for W in wins:
        s,e_=W[0][0],W[-1][0]
        dead={x['v'] for x in deaths if s<=x['r']<=e_+1}
        for side in ('us','them'):
            mine=[h for h in W if (team[h[1]]==us)==(side=='us')]
            tot=sum(h[3] for h in mine)
            if tot<=0: continue
            per=Counter(); 
            for h in mine: per[h[2]]+=h[3]
            top=per.most_common(1)[0][1]
            todead=sum(v for k,v in per.items() if k in dead)
            out.append((side,r['opp'],tot,top/tot,todead/tot,len(per),len(dead&set(per))))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,games()) for x in o]
    for side in ('us','them'):
        X=[x for x in res if x[0]==side and x[5]>=2]
        T=sum(x[2] for x in X)
        print(side,'windows with >=2 targets hit:',len(X),'dmg-weighted top-target share %.2f'%(sum(x[2]*x[3] for x in X)/T),'share of dmg on targets that died %.2f'%(sum(x[2]*x[4] for x in X)/T))
        X=[x for x in res if x[0]==side]; T=sum(x[2] for x in X)
        print('   all windows: share of dmg on targets that died %.2f; total dmg %.0f'%(sum(x[2]*x[4] for x in X)/T,T))
        for o in ('Fish','Mite','UoS','PBG'):
            Y=[x for x in X if x[1]==o]; T=sum(x[2] for x in Y); print('   ',o,'dmg->dead %.2f'%(sum(x[2]*x[4] for x in Y)/T))
