"""Q5 (extract, both teams): territory. Share of alive off-spawn body-rounds on the enemy's half (walk distance to
the enemy spawn below that to our own), share of captures (and captured gems) from groups on the enemy's half
(map group `side`), by opponent and by phase."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
def one(g):
    G=Game(g); us=G.us; acc=defaultdict(lambda:[0,0,0,0,0,0])
    side={gg['id']:gg['side'] for gg in G.mp['groups']}
    for i in range(1,G.N,2):
        ph=0 if G.rnd[i]<300 else (1 if G.rnd[i]<800 else 2)
        for c in G.team:
            t=G.team[c]; p=G.pos(c,i)
            if not p or G.on_spawn(t,p): continue
            A=acc[('us' if t==us else 'them',ph)]; A[0]+=1
            if G.sf(1-t).get(p,999)<G.sf(t).get(p,999): A[1]+=1
    for e in G.ev:
        if e['k']!='capture': continue
        t=e['team']; ph=0 if e['r']<300 else (1 if e['r']<800 else 2); A=acc[('us' if t==us else 'them',ph)]
        gm=sum(s[1] for s in e['shares']); A[2]+=1; A[4]+=gm
        if side[e['g']]==1-t: A[3]+=1; A[5]+=gm
    return dict(opp=G.opp,acc={str(k):v for k,v in acc.items()})
if __name__=='__main__':
    res=pmap(one,games())
    for o in ('all','Fish','Mite','UoS','PBG'):
        tot=defaultdict(lambda:[0]*6)
        for x in res:
            if o!='all' and x['opp']!=o: continue
            for k,v in x['acc'].items():
                k=eval(k)
                for j in range(6): tot[k[0]][j]+=v[j]; tot[k][j]+=v[j]
        print(o,' | '.join(f"{s}: time on enemy half {tot[s][1]/tot[s][0]:.2f}, captures there {tot[s][3]/tot[s][2]:.2f}, captured gems there {tot[s][5]/max(1,tot[s][4]):.2f}" for s in('us','them')))
        if o=='all':
            for ph in (0,1,2): print('  phase',ph,' | '.join(f"{s}: enemy half time {tot[(s,ph)][1]/tot[(s,ph)][0]:.2f} gems there {tot[(s,ph)][5]/max(1,tot[(s,ph)][4]):.2f}" for s in('us','them')))
