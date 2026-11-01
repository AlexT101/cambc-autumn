import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def order(R,ri,r,ids,team):
    i=ri.get(r-1)
    prio={c['id']:(c['prio'][i] if i is not None else 0) for c in R['champions']}
    T=[sorted([c for c in ids if team[c]==tm],key=lambda c:(-prio[c],c)) for tm in (0,1)]
    f=0 if r%2==1 else 1; a,b=T[f],T[1-f]; out=[]
    for k in range(max(len(a),len(b))): out+=([a[k]] if k<len(a) else [])+([b[k]] if k<len(b) else [])
    return out
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']
    team={c['id']:c['team'] for c in m['champions']}; ids=list(team)
    ri={rn:i for i,rn in enumerate(R['round'])}
    out=[]
    for e in events(d):
        if e['k']!='death' or e.get('linked') is not None or e.get('by') is None: continue
        v,k,rn,t=e['v'],e['by'],e['r'],e['t']
        o=order(R,ri,rn,ids,team); 
        # victim's last turn: in this round if its index < t, else previous round
        if o.index(v)<t: vt=(rn,o.index(v))
        else: vt=(rn-1,order(R,ri,rn-1,ids,team).index(v))
        # killer turns strictly between vt and (rn,t) inclusive of the death turn
        n=0
        if vt[0]==rn-1:
            o1=order(R,ri,rn-1,ids,team); n+= o1.index(k)>vt[1]
        n+= o.index(k)<=t if vt[0]==rn-1 else (vt[1]<o.index(k)<=t)
        out.append(('us' if team[v]==us else 'them', r['opp'], n))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,games()) for x in o]
    for s in ('us','them'):
        X=[x for x in res if x[0]==s]; c=Counter(x[2] for x in X); print(s,len(X),{k:'%.2f'%(v/len(X)) for k,v in sorted(c.items())})
