"""Holds under pressure (both teams, extract). A hold starts at capture_hold (team T, group g) and ends at the
capture (paid) or the next capture_reset of T on g. Pressured = an enemy champion within 3 of the group's tiles
at a round end during the hold. Local count = T's / enemy champions within 6 of the tiles at the first pressured
round end. Outcome: paid, walked (reset, leaver alive), contested, died."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
def one(g):
    G=Game(g); us=G.us
    gt={gg['id']:set(map(tuple,gg['tiles'])) for gg in G.mp['groups']}
    out=[]; open_={}
    for e in G.ev:
        k=e['k']
        if k=='capture_hold': open_[(e['g'],e['team'])]=e['r']
        elif k in('capture','capture_reset') and (e['g'],e['team']) in open_:
            t=e['team']; r0=open_.pop((e['g'],t)); r1=e['r']; tiles=gt[e['g']]
            if k=='capture': oc='paid'
            elif e.get('contested'): oc='contested'
            else:
                i=G.idx.get(r1)
                lv=[c for c in G.team if G.team[c]==t and i and G.pos(c,i-1) in tiles and G.pos(c,i) not in tiles]
                oc='died' if lv and not G.ch[lv[0]]['alive'][i] else 'walked'
            pr=None
            for r in range(r0,r1):
                i=G.idx.get(r)
                if i is None: continue
                ds=[min(C.cheb(G.pos(c,i),q) for q in tiles) for c in G.team if G.team[c]!=t and G.pos(c,i)]
                if ds and min(ds)<=3:
                    own=sum(1 for c in G.team if G.team[c]==t and G.pos(c,i) and min(C.cheb(G.pos(c,i),q) for q in tiles)<=6)
                    en=sum(1 for d in ds if d<=6); pr=(r,own,en); break
            out.append(dict(side='us' if t==us else 'them',oc=oc,pr=pr,r0=r0,r1=r1,g=e['g'],dir=G.dir,opp=G.opp,map=G.mapname))
    return out
if __name__=='__main__':
    res=[x for o in pmap(one,games()) for x in o]
    json.dump(res,open(CACHE+'/../q1_holds.json','w'))
    for side in('us','them'):
        Z=[x for x in res if x['side']==side]; P=[x for x in Z if x['pr']]
        print(side,'holds',len(Z),'paid %.2f'%(sum(x['oc']=='paid' for x in Z)/len(Z)),'pressured',len(P),Counter(x['oc'] for x in P))
        for lab,f in (('outnumbered locally',lambda p:p[1]<p[2]),('equal',lambda p:p[1]==p[2]),('more',lambda p:p[1]>p[2])):
            W=[x for x in P if f(x['pr'])]
            if W: print(f"   {lab:20s} n={len(W):5d} paid {sum(x['oc']=='paid' for x in W)/len(W):.2f} walked {sum(x['oc']=='walked' for x in W)/len(W):.2f} contested {sum(x['oc']=='contested' for x in W)/len(W):.2f} died {sum(x['oc']=='died' for x in W)/len(W):.2f}")
    # generality: per map, paid share under pressure at equal-or-better local numbers
    pm=defaultdict(lambda:{'us':[0,0],'them':[0,0]})
    for x in res:
        if x['pr'] and x['pr'][1]>=x['pr'][2]: pm[x['map']][x['side']][0]+=1; pm[x['map']][x['side']][1]+=x['oc']=='paid'
    m=[k for k,v in pm.items() if v['us'][0]>=5 and v['them'][0]>=5]
    print('maps with >=5 each (pressured, not outnumbered):',len(m),'maps where our paid share < theirs:',sum(pm[k]['us'][1]/pm[k]['us'][0]<pm[k]['them'][1]/pm[k]['them'][0] for k in m))
