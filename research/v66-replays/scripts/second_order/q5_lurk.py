"""Q5 (extract, both teams): where and how kills happen.
- lurk kill: the killer's positions over the 15 rounds before the kill all within 3 tiles of its kill-round
  position (it waited there), and was not on its own spawn.
- side: the victim's death tile on its own half (spawn walk distance less than to the enemy spawn) or the enemy's.
- victim's activity in the 10 rounds before: attacked a camp, held a capture tile, or neither (travel)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
def one(g):
    G=Game(g); us=G.us; out=[]
    gt=set(tuple(t) for gg in G.mp['groups'] for t in gg['tiles'])
    campatk=defaultdict(set)
    for e in G.ev:
        if e['k'] in('attack','cast') and (e.get('camp') is not None or e.get('cdmg')): campatk[e['a']].add(e['r'])
    for e in G.deaths:
        if e.get('by') is None or not e.get('at'): continue
        v=e['v']; k=e['by']; i=G.idx.get(e['r'],G.N-1)
        kp=G.pos(k,i-1) or G.pos(k,i)
        if kp is None: continue
        win=[G.pos(k,j) for j in range(max(0,i-16),i)]
        lurk=all(p is not None and C.cheb(p,kp)<=3 for p in win) and not G.on_spawn(G.team[k],kp)
        at=tuple(e['at']); tv=G.team[v]
        own_half=G.sf(tv).get(at,999)<G.sf(1-tv).get(at,999)
        act='camp' if any(r in campatk[v] for r in range(e['r']-10,e['r']+1)) else ('hold' if any(G.pos(v,j) in gt for j in range(max(0,i-10),i)) else 'travel')
        out.append(dict(side='us' if tv==us else 'them',lurk=lurk,own_half=own_half,act=act,r=e['r'],dir=G.dir,map=G.mapname,opp=G.opp))
    return out
if __name__=='__main__':
    res=[y for o in pmap(one,games()) for y in o]
    for s in('us','them'):
        Z=[x for x in res if x['side']==s]; n=len(Z)
        print(f"{s} deaths to champions {n} ({n/412:.1f}/game): killer lurked {sum(x['lurk'] for x in Z)/n:.2f} ({sum(x['lurk'] for x in Z)/412:.2f}/game); on victim's own half {sum(x['own_half'] for x in Z)/n:.2f}; victim activity {dict((k,round(v/n,2)) for k,v in Counter(x['act'] for x in Z).items())}")
        L=[x for x in Z if x['lurk']]; print(f"    lurk kills: own half {sum(x['own_half'] for x in L)/len(L):.2f}, activity {dict((k,round(v/len(L),2)) for k,v in Counter(x['act'] for x in L).items())}")
    print('own-half share of deaths by phase (r<300, 300-800, 800+):')
    for s in('us','them'):
        print(' ',s,[round(sum(x['own_half'] for x in res if x['side']==s and lo<=x['r']<hi)/max(1,sum(1 for x in res if x['side']==s and lo<=x['r']<hi)),2) for lo,hi in((0,300),(300,800),(800,9999))])
    pm=defaultdict(lambda:{'us':[0,0],'them':[0,0]})
    for x in res: pm[x['map']][x['side']][0]+=1; pm[x['map']][x['side']][1]+=x['own_half']
    m=[k for k,v in pm.items() if v['us'][0]>=10 and v['them'][0]>=10]
    print(' maps (>=10 deaths each):',len(m),'our own-half share higher on',sum(pm[k]['us'][1]/pm[k]['us'][0]>pm[k]['them'][1]/pm[k]['them'][0] for k in m))
