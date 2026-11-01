"""Q4 (extract, both teams): repeated deaths at the same place, rematches with the same killer, tribute cancels,
bags lost far from altars.
- repeat_site: a death within 5 tiles (Chebyshev) of an earlier death of the same team (same unit / any unit).
- same_fight: the unit's previous death was within 6 tiles, the gap at most 150 rounds, and the same killer unit.
- tribute: starts, cancels by cause, repeated cancels (>=2 cancels by one body within 30 rounds).
- bag loss: deaths carrying >= 20 gems; altar walk distance at death; the bag's age (rounds since it was under
  a quarter of its final size)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
import statistics as st
from collections import deque
def altar_field(mp):
    W,H=mp['width'],mp['height']
    blk=set(map(tuple,mp['walls']))|set(map(tuple,mp['holes']))|set(map(tuple,mp['altars']))
    D={}; q=deque()
    for a in mp['altars']:
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                n=(a[0]+dx,a[1]+dy)
                if 0<=n[0]<W and 0<=n[1]<H and n not in blk and n not in D: D[n]=0; q.append(n)
    while q:
        p=q.popleft()
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                n=(p[0]+dx,p[1]+dy)
                if 0<=n[0]<W and 0<=n[1]<H and n not in blk and n not in D: D[n]=D[p]+1; q.append(n)
    return D
def one(g):
    G=Game(g); us=G.us; AF=altar_field(G.mp)
    side=lambda c:'us' if G.team[c]==us else 'them'
    deaths=sorted(G.deaths,key=lambda e:e['s'])
    rows=[]; prev=defaultdict(list)
    for e in deaths:
        u=G.unit[e['v']]; t=G.team[u]; at=tuple(e['at']) if e.get('at') else None
        killer=G.unit.get(e.get('by')) if e.get('by') is not None else 'camp'
        same_unit=[p for p in prev[u] if at and C.cheb(p['at'],at)<=5]
        any_team=[p for v in G.units[t] for p in prev[v] if at and C.cheb(p['at'],at)<=5]
        pu=prev[u][-1] if prev[u] else None
        same_fight=bool(pu and at and C.cheb(pu['at'],at)<=6 and e['r']-pu['r']<=150 and pu['killer']==killer and killer!='camp')
        rows.append(dict(side=side(u),r=e['r'],at=at,name=G.name[u],killer=G.name.get(killer,'camp') if killer!='camp' else 'camp',rep_unit=bool(same_unit),rep_team=bool(any_team),
                         same_fight=same_fight,nprev=len(prev[u]),gems=e.get('gems',0),altar=AF.get(at) if at else None,dir=G.dir,opp=G.opp,map=G.mapname))
        if at: prev[u].append(dict(at=at,r=e['r'],killer=killer))
    # bag ages
    for row,e in zip(rows,deaths):
        if row['gems']>=20:
            c=e['v']; i=G.idx.get(e['r'],G.N-1)-1; gm=G.ch[c]['gems']; k=i
            while k>0 and gm[k]>=row['gems']/4: k-=1
            row['bag_age']=i-k
    trib=[]
    for e in G.ev:
        if e['k'] in('tribute_start','tribute_cancel','tribute_end'): trib.append((side(e['a']),e['k'],e.get('cause'),e['r'],e['a'],e.get('gems')))
    return dict(deaths=rows,trib=trib,opp=G.opp,map=G.mapname)
if __name__=='__main__':
    res=pmap(one,games()); json.dump(res,open(CACHE+'/../q4.json','w'))
    D=[d for x in res for d in x['deaths']]
    for s in('us','them'):
        Z=[d for d in D if d['side']==s]; n=len(Z)
        print(f"{s}: deaths {n} ({n/412:.1f}/game). repeat site same unit {sum(d['rep_unit'] for d in Z)/n:.2f}, any of team {sum(d['rep_team'] for d in Z)/n:.2f}; same fight (place+killer, <=150r) {sum(d['same_fight'] for d in Z)/n:.3f}")
        Zs=[d for d in Z if d['nprev']>=1]
        print(f"   of deaths with a previous death of that unit ({len(Zs)}): same unit within 5 tiles {sum(d['rep_unit'] for d in Zs)/len(Zs):.2f}, same fight {sum(d['same_fight'] for d in Zs)/len(Zs):.3f}")
        B=[d for d in Z if d['gems']>=20]
        print(f"   bags>=20 lost: {len(B)/412:.2f}/game, gems {sum(d['gems'] for d in B)/412:.1f}/game; median altar dist {st.median([d['altar'] for d in B if d['altar'] is not None])}; median bag age {st.median([d['bag_age'] for d in B])}; non-Prism {sum(d['gems'] for d in B if d['name']!='Prism')/412:.1f}/game, dist>=10 {sum(d['gems'] for d in B if (d['altar'] or 0)>=10)/412:.1f}")
        T=[t for x in res for t in x['trib'] if t[0]==s]
        st_=sum(t[1]=='tribute_start' for t in T); ca=Counter(t[2] for t in T if t[1]=='tribute_cancel')
        print(f"   tributes started {st_/412:.1f}/game, cancelled {sum(ca.values())/412:.2f}/game {dict(ca)}")
    # map generality of same-unit repeat and same-fight
    pm=defaultdict(lambda:{'us':[0,0],'them':[0,0]})
    for d in D: pm[d['map']][d['side']][0]+=1; pm[d['map']][d['side']][1]+=d['rep_unit']
    m=[k for k,v in pm.items() if v['us'][0]>=10 and v['them'][0]>=10]
    print('maps (>=10 deaths each):',len(m),'our same-unit repeat share higher on',sum(pm[k]['us'][1]/pm[k]['us'][0]>pm[k]['them'][1]/pm[k]['them'][0] for k in m))
    # repeat site normalised by number of prior deaths (more deaths -> more chances)
    for s in ('us','them'):
        for k in (1,2,3,4):
            Z=[d for d in D if d['side']==s and d['nprev']==k]
            if Z: print(s,'prior deaths',k,'n',len(Z),'same-unit repeat %.2f same fight %.3f'%(sum(d['rep_unit'] for d in Z)/len(Z),sum(d['same_fight'] for d in Z)/len(Z)))
