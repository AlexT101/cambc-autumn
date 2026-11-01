import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); us=r['us']
    pr=[c['id'] for c in m['champions'] if c['team']==us and c['name']=='Prism']
    if not pr: return None
    p=pr[0]; o=Counter(); bags=[]
    for e in events(d):
        if e['k']=='tribute_end' and e['a']==p: o['trib']+=e['gems']; o['ntrib']+=1; bags.append(e['gems'])
        if e['k']=='death' and e['v']==p: o['lost']+=e['gems']; o['ndeath']+=1; o['lost_big']+= e['gems'] if e['gems']>=50 else 0
        if e['k']=='tribute_cancel' and e['a']==p: o['cancel']+=1
    c=m['champions'][p]['stats']
    o['collected']=c['collectedGems']
    return r['opp'],r['won'],o,bags
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for x in ex.map(one,games()) if x]
    for won in (True,False):
        X=[x for x in res if x[1]==won]; n=len(X); T=Counter()
        for x in X: T.update(x[2])
        import statistics as st
        print('won' if won else 'lost',n,'games; per game: collected %.0f tributed %.0f lost on death %.0f (bags>=50: %.0f) deaths %.2f tributes %.1f cancels %.2f'%(T['collected']/n,T['trib']/n,T['lost']/n,T['lost_big']/n,T['ndeath']/n,T['ntrib']/n,T['cancel']/n))
        bags=[b for x in X for b in x[3]]; print('   tribute bag quartiles',st.quantiles(bags,n=4) if bags else None)
