"""Our walked-off pressured holds (from q1_holdtrace.json): could the hold have paid?
For each walk: rounds left to payout (capture_reset left), our stand sim's tku (their turns to kill our side) from
the deciding TE home, and the nearest enemy's Chebyshev distance to the group's tiles at the end of the round
before the reset ('cannot contest' = distance > left + 1: no walk plus one dash reaches a tile in time).
Also the extract's truth: did an enemy stand on a tile within `left` rounds after the reset."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
H=json.load(open(CACHE+'/../q1_holdtrace.json'))
M={k:g for k,g in trace_keys()}
def one(key):
    G=Game(M[key]); gt={gg['id']:set(map(tuple,gg['tiles'])) for gg in G.mp['groups']}; out=[]
    for x in H:
        if x['key']!=key or x['oc']!='walked': continue
        tiles=gt[x['g']]; r1=x['r1']; left=x['left'] or 0; i=G.idx[r1]
        en=[min(C.cheb(G.pos(c,i-1),q) for q in tiles) for c in G.team if G.team[c]!=G.us and G.pos(c,i-1)]
        dmin=min(en) if en else 99
        came=False
        for r in range(r1,r1+left+1):
            j=G.idx.get(r)
            if j is None: break
            if any(G.pos(c,j) in tiles for c in G.team if G.team[c]!=G.us): came=True
        h=x['homes'][-1] if x['homes'] else None
        tku=None
        if h and h[3]:
            try: tku=int(h[3].split(':')[1])
            except: pass
        out.append(dict(key=key,g=x['g'],r1=r1,left=left,why=h[2] if h else None,tku=tku,dmin=dmin,came=came,stolen=x['stolen'],hd=x['hd'],gems=x['gems'],pr=x['pr']))
    return out
if __name__=='__main__':
    res=[y for o in pmap(one,sorted({x['key'] for x in H if x['oc']=='walked'})) for y in o]
    json.dump(res,open(CACHE+'/../q1_holdwalk.json','w'))
    n=len(res); print('walked pressured holds',n)
    cc=[x for x in res if x['dmin']>x['left']+1]
    print(f"enemy could not reach a tile before payout (dist > left+1): {len(cc)} ({len(cc)/n:.2f}); of those an enemy did stand on a tile within left: {sum(x['came'] for x in cc)}; stolen later {sum(x['stolen'] for x in cc)/max(1,len(cc)):.2f}; leaver died<=15 {sum(x['hd'] for x in cc)/max(1,len(cc)):.2f}")
    print(' by reason',Counter(x['why'] for x in cc), 'left',Counter(x['left'] for x in cc))
    sl=[x for x in res if x['why'] in('stand_lost','stand_falls') and x['tku']]
    print(f"stand_* walks with tku known {len(sl)}: tku > left+1 (our sim: they need longer to kill us than the hold needs) {sum(x['tku']>x['left']+1 for x in sl)/len(sl):.2f}")
    both=[x for x in sl if x['tku']>x['left']+1 and x['dmin']>x['left']+1]
    print(f"  both (survives and cannot be contested in time): {len(both)} of {n} walks; gems {sum(x['gems'] for x in both)}; over {len({x['key'] for x in H})} traced games")
    any_came=[x for x in res if x['came']]; print('enemy did step on a tile within left rounds:',len(any_came)/n)
    for x in both[:10]: print(x)
