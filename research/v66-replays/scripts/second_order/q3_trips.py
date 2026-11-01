"""Q3: home trips (extract, both teams, per body).
A visit = an alive stay on own spawn that does not start with a respawn or at game start. Its trip runs from
`start` (walking back from arrival over rounds whose spawn distance does not increase, then dropping leading
rounds where it stood still) to arrival, the stay on spawn, and the walk out until the spawn distance first
reaches the start distance again (or 80 rounds). Mode: recall (a recall_end at arrival) or walk."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
import statistics as st
def one(g):
    G=Game(g); us=G.us; out=[]; alive_rounds={'us':0,'them':0}
    rec_end=defaultdict(set)
    for e in G.ev:
        if e['k']=='recall_end': rec_end[e['a']].add(e['r'])
    shop=defaultdict(set)
    for e in G.ev:
        if e['k']=='shop': shop[e['a']].add(e['r'])
    for c in G.team:
        t=G.team[c]; side='us' if t==us else 'them'; F=G.sf(t); A=G.ch[c]
        alive_rounds[side]+=sum(A['alive'])
        dist=[F.get(G.pos(c,i),None) if G.pos(c,i) else None for i in range(G.N)]
        on=[G.on_spawn(t,G.pos(c,i)) for i in range(G.N)]
        i=1
        while i<G.N:
            if on[i] and not on[i-1] and A['alive'][i-1] and dist[i-1] is not None:
                arr=i
                # stay
                j=i
                while j<G.N and on[j] and A['alive'][j]: j+=1
                dwell=j-i
                # walk back
                s=i-1
                while s-1>=0 and dist[s-1] is not None and dist[s] is not None and dist[s-1]>=dist[s] and A['alive'][s-1]: s-=1
                while s<i-1 and dist[s]==dist[s+1]: s+=1
                d0=dist[s]; hp0=A['hp'][s]/A['maxHp'][s]
                mode='recall' if G.rnd[arr] in rec_end[c] else 'walk'
                # return
                k=j; ret=None
                while k<G.N and k<j+80 and A['alive'][k]:
                    if dist[k] is not None and dist[k]>=d0: ret=k-j; break
                    k+=1
                bought=any(G.rnd[x] in shop[c] for x in range(arr,j+1) if x<G.N)
                out.append(dict(side=side,c=c,name=G.name[c],r=G.rnd[arr],d0=d0,hp0=round(hp0,3),walk=arr-s,dwell=dwell,ret=ret,mode=mode,shop=bought,hpa=A['hp'][min(j,G.N-1)-1]/A['maxHp'][min(j,G.N-1)-1]))
                i=j
            i+=1
    return dict(trips=out,alive=alive_rounds,opp=G.opp,map=G.mapname,dir=G.dir,won=G.won)
if __name__=='__main__':
    res=pmap(one,games())
    json.dump(res,open(CACHE+'/../q3.json','w'))
    for side in('us','them'):
        Z=[t for x in res for t in x['trips'] if t['side']==side]; AR=sum(x['alive'][side] for x in res)
        tot=sum(t['walk']+t['dwell']+(t['ret'] if t['ret'] is not None else 0) for t in Z)
        print(f"{side}: trips {len(Z)} ({1000*len(Z)/AR:.2f} per 1000 alive body-rounds), recall share {sum(t['mode']=='recall' for t in Z)/len(Z):.2f}, shop on visit {sum(t['shop'] for t in Z)/len(Z):.2f}")
        print(f"   time on trips {100*tot/AR:.1f}% of alive time (walk-in {100*sum(t['walk'] for t in Z)/AR:.1f}%, on spawn {100*sum(t['dwell'] for t in Z)/AR:.1f}%, walk-out {100*sum(t['ret'] or 0 for t in Z)/AR:.1f}%)")
        print(f"   start: median dist {st.median(t['d0'] for t in Z)}, median hp {st.median(t['hp0'] for t in Z):.2f}; hp<0.4 {sum(t['hp0']<0.4 for t in Z)/len(Z):.2f}, hp>=0.8 {sum(t['hp0']>=0.8 for t in Z)/len(Z):.2f}; median walk-in {st.median(t['walk'] for t in Z)} dwell {st.median(t['dwell'] for t in Z)} out {st.median([t['ret'] for t in Z if t['ret'] is not None])}")
        for mode in ('walk','recall'):
            W=[t for t in Z if t['mode']==mode]
            print(f"   {mode}: n={len(W)} dist {st.median(t['d0'] for t in W)} hp {st.median(t['hp0'] for t in W):.2f} walk-in {st.median(t['walk'] for t in W)} dwell {st.median(t['dwell'] for t in W)}")
        # far & healthy-ish trips (walked home from >15 at hp>=0.35)
        W=[t for t in Z if t['mode']=='walk' and t['d0']>=15]
        print(f"   walked home from >=15 steps: {1000*len(W)/AR:.2f}/1000 alive rounds, median hp {st.median(t['hp0'] for t in W):.2f}, median walk-in {st.median(t['walk'] for t in W)}")
    for o in ('Fish','Mite','UoS','PBG'):
        s=[]
        for side in('us','them'):
            Z=[t for x in res if x['opp']==o for t in x['trips'] if t['side']==side]; AR=sum(x['alive'][side] for x in res if x['opp']==o)
            s.append(f"{side} {100*sum(t['walk']+t['dwell']+(t['ret'] or 0) for t in Z)/AR:.1f}%")
        print(o,' '.join(s))
