"""Q5 (extract, both teams): regrouping and follow-through.
- spread by manpower diff: each alive off-spawn unit's nearest alive ally (Chebyshev), sampled every 3 rounds,
  and the share of units with an enemy within 8 and no ally within 8 ('exposed').
- follow-through: after each kill (non-camp) at tile L in round K, within 20 rounds and 10 tiles of L:
  further deaths of the killer's team vs the victim's team."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
import statistics as st
def one(g):
    G=Game(g); us=G.us; acc=defaultdict(lambda:[0,0,0,[]])  # (side,diff)->[samples, exposed, ally<=4, nearest list]
    for i in range(1,G.N,3):
        for t in (0,1):
            d=max(-2,min(2,G.alive_units(t,i-1)-G.alive_units(1-t,i-1)))
            side='us' if t==us else 'them'
            for u in G.units[t]:
                p=G.pos(u,i)
                if not p or G.on_spawn(t,p): continue
                al=[C.cheb(p,G.pos(v,i)) for v in G.units[t] if v!=u and G.pos(v,i)]
                en=[C.cheb(p,G.pos(v,i)) for v in G.team if G.team[v]!=t and G.pos(v,i)]
                A=acc[(side,d)]; A[0]+=1
                na=min(al) if al else 99
                if en and min(en)<=8 and na>8: A[1]+=1
                if na<=4: A[2]+=1
                A[3].append(min(na,40))
    ft=[]
    ds=sorted([e for e in G.deaths if e.get('by') is not None and e.get('at')],key=lambda e:e['s'])
    for j,e in enumerate(ds):
        kt=G.team[e['by']]; L=e['at']; K=e['r']
        nxt=[x for x in ds[j+1:] if x['r']-K<=20 and C.cheb(x['at'],L)<=10]
        ft.append(dict(killer_side='us' if kt==us else 'them',killer_more=sum(G.team[x['v']]!=kt for x in nxt),killer_lost=sum(G.team[x['v']]==kt for x in nxt),r=K))
    return dict(acc={str(k):[v[0],v[1],v[2],st.median(v[3]) if v[3] else None,len(v[3])] for k,v in acc.items()},ft=ft,opp=G.opp)
if __name__=='__main__':
    res=pmap(one,games())
    json.dump(res,open(CACHE+'/../q5_regroup.json','w'))
    tot=defaultdict(lambda:[0,0,0,[]])
    for x in res:
        for k,v in x['acc'].items():
            A=tot[eval(k)]; A[0]+=v[0]; A[1]+=v[1]; A[2]+=v[2]
            if v[3] is not None: A[3]+= [v[3]]*v[4]
    for d in (-2,-1,0,1,2):
        print(d,' | '.join(f"{s}: n={tot[(s,d)][0]} exposed {tot[(s,d)][1]/tot[(s,d)][0]:.3f} ally<=4 {tot[(s,d)][2]/tot[(s,d)][0]:.2f} med nearest(game medians) {st.median(tot[(s,d)][3])}" for s in('us','them')))
    F=[f for x in res for f in x['ft']]
    for s in('us','them'):
        Z=[f for f in F if f['killer_side']==s]
        print(f"after a kill by {s} (n={len(Z)}): within 20r/10 tiles killer team kills again {sum(f['killer_more'] for f in Z)/len(Z):.2f}, loses {sum(f['killer_lost'] for f in Z)/len(Z):.2f}; P(lose one) {sum(f['killer_lost']>0 for f in Z)/len(Z):.2f}")
