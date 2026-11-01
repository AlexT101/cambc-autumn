"""Q1 (extract, both teams): productive time by manpower diff. Per alive body-round (off spawn and on), working =
attacked or cast at a camp that round, or stood on a camp group's tile (a hold) at the round end.
Also the share of body-rounds within 3 of own spawn (sheltering) and channelling a recall."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
def one(g):
    G=Game(g); us=G.us
    gt=set(tuple(t) for gg in G.mp['groups'] for t in gg['tiles'])
    ca=set()
    for e in G.ev:
        if e['k'] in('attack','cast') and (e.get('camp') is not None or e.get('cdmg')): ca.add((e['a'],e['r']))
    acc=defaultdict(lambda:[0,0,0,0])
    for i in range(1,G.N):
        r=G.rnd[i]
        for t in (0,1):
            d=max(-2,min(2,G.alive_units(t,i-1)-G.alive_units(1-t,i-1)))
            k=('us' if t==us else 'them',d)
            for c in G.team:
                if G.team[c]!=t: continue
                p=G.pos(c,i)
                if p is None: continue
                A=acc[k]; A[0]+=1
                if (c,r) in ca or p in gt: A[1]+=1
                if G.sf(t).get(p,99)<=3: A[2]+=1
                if G.ch[c]['chan'][i]==1: A[3]+=1
    return {str(k):v for k,v in acc.items()}
if __name__=='__main__':
    res=pmap(one,games()); tot=defaultdict(lambda:[0,0,0,0])
    for x in res:
        for k,v in x.items():
            for j in range(4): tot[eval(k)][j]+=v[j]
    for d in (-2,-1,0,1,2):
        print(f'{d:+d} '+' | '.join(f"{s}: working {tot[(s,d)][1]/tot[(s,d)][0]:.3f} near spawn {tot[(s,d)][2]/tot[(s,d)][0]:.3f} recall {tot[(s,d)][3]/tot[(s,d)][0]:.3f}" for s in('us','them')))
