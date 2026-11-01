"""Q2: deaths after a respawn (extract, both teams).
For each respawn (champion c of team T at round R; C&I counted on Cassi): death within 30/60 rounds; at death,
allies / enemies within 8; nearest-ally distance over the 60 rounds after respawn vs the team's overall
alive time; and hazard per alive round in the 60 rounds after respawn vs overall."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
import statistics as st
def near(G,c,i,team_same,rad=8):
    p=G.pos(c,i)
    if p is None: return None
    return sum(1 for d in G.team if d!=c and G.unit[d]==d and (G.team[d]==G.team[c])==team_same and G.pos(d,i) and C.cheb(G.pos(d,i),p)<=rad)
def one(g):
    G=Game(g); us=G.us; out=[]; base=defaultdict(lambda:[0,0])  # side-> [alive rounds, deaths]
    dr=defaultdict(list)
    for e in G.deaths: dr[G.unit[e['v']]].append(e)
    for u in G.units[0]+G.units[1]:
        side='us' if G.team[u]==us else 'them'
        base[side][0]+=sum(G.ch[u]['alive']); base[side][1]+=len(dr[u])
    nd=defaultdict(list)  # side -> nearest ally dist samples (every 5 rounds) overall
    for u in G.units[0]+G.units[1]:
        side='us' if G.team[u]==us else 'them'
        for i in range(0,G.N,5):
            p=G.pos(u,i)
            if not p or G.on_spawn(G.team[u],p): continue
            ds=[C.cheb(p,G.pos(d,i)) for d in G.units[G.team[u]] if d!=u and G.pos(d,i)]
            if ds: nd[side].append(min(ds))
    for e in G.ev:
        if e['k']!='respawn' or G.unit[e['a']]!=e['a']: continue
        c=e['a']; R=e['r']; side='us' if G.team[c]==us else 'them'
        nxt=[x for x in dr[c] if x['r']>R]
        dd=nxt[0] if nxt else None
        gap=dd['r']-R if dd else None
        # teammates alive at respawn
        i0=G.idx.get(R,0)
        mates_alive=sum(1 for d in G.units[G.team[c]] if d!=c and G.ch[d]['alive'][i0])
        # nearest ally distance in the 60 rounds after respawn (off spawn), every 5 rounds
        samp=[]
        for r in range(R+5,R+61,5):
            i=G.idx.get(r)
            if i is None: break
            p=G.pos(c,i)
            if not p or G.on_spawn(G.team[c],p): continue
            ds=[C.cheb(p,G.pos(d,i)) for d in G.units[G.team[c]] if d!=c and G.pos(d,i)]
            if ds: samp.append(min(ds))
        at=None
        if dd and gap<=60:
            i=G.idx.get(dd['r'])-1
            at=(near(G,c,i,True),near(G,c,i,False),'camp' if dd.get('camp') is not None else G.name.get(dd.get('by')))
        out.append(dict(side=side,c=c,name=G.name[c],R=R,gap=gap,mates=mates_alive,samp=samp,at=at,opp=G.opp,map=G.mapname,dir=G.dir,alive_after=sum(G.ch[c]['alive'][G.idx[r]] for r in range(R,R+60) if r in G.idx)))
    return dict(resp=out,base={k:v for k,v in base.items()},nd={k:v for k,v in nd.items()})
if __name__=='__main__':
    res=pmap(one,games())
    json.dump(res,open(CACHE+'/../q2.json','w'))
    base=defaultdict(lambda:[0,0]); nd=defaultdict(list); R=[]
    for x in res:
        for k,v in x['base'].items(): base[k][0]+=v[0]; base[k][1]+=v[1]
        for k,v in x['nd'].items(): nd[k]+=v
        R+=x['resp']
    for side in('us','them'):
        Z=[x for x in R if x['side']==side]; n=len(Z)
        bh=base[side][1]/base[side][0]*60
        d30=sum(x['gap'] is not None and x['gap']<=30 for x in Z)/n; d60=sum(x['gap'] is not None and x['gap']<=60 for x in Z)/n
        ar=sum(x['alive_after'] for x in Z); dn=sum(1 for x in Z if x['gap'] is not None and x['gap']<60)
        print(f"{side}: respawns {n} ({n/412:.1f}/game). die within 30: {d30:.3f}, within 60: {d60:.3f}; hazard per 60 alive rounds after respawn {dn/ar*60:.3f} vs overall {bh:.3f}")
        print(f"   nearest ally (off spawn, median): first 60 after respawn {st.median([s for x in Z for s in x['samp']])}, overall {st.median(nd[side])}; share >8 tiles: {sum(s>8 for x in Z for s in x['samp'])/max(1,sum(len(x['samp']) for x in Z)):.2f} vs {sum(s>8 for s in nd[side])/len(nd[side]):.2f}")
        A=[x['at'] for x in Z if x['at']]
        print(f"   deaths within 60 of respawn: {len(A)}; alone (0 allies within 8) {sum(a[0]==0 for a in A)/len(A):.2f}; enemies>=2 {sum(a[1]>=2 for a in A)/len(A):.2f}; camp {sum(a[2]=='camp' for a in A)/len(A):.2f}")
        for m in (0,1,2,3,4):
            W=[x for x in Z if x['mates']==m]
            if len(W)>30: print(f"   mates alive at respawn {m}: n={len(W)} die<=60 {sum(x['gap'] is not None and x['gap']<=60 for x in W)/len(W):.3f}")
    for o in ('Fish','Mite','UoS','PBG'):
        s=[]
        for side in('us','them'):
            Z=[x for x in R if x['side']==side and x['opp']==o]
            s.append(f"{side} {sum(x['gap'] is not None and x['gap']<=60 for x in Z)/len(Z):.3f} (n={len(Z)})")
        print(o,' '.join(s))
