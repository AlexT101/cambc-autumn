import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    m=meta(r['dir']); us=r['us']
    pr=[c for c in m['champions'] if c['team']==us and c['name']=='Prism']
    if not pr: return None
    p=pr[0]
    R=rounds(r['dir']); c=[x for x in R['champions'] if x['id']==p['id']][0]
    mx=max(c['gems']); 
    return r['won'],p['gems'],mx,r['gems'][us],r['gems'][1-us]
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for x in ex.map(one,games()) if x]
    import statistics as st
    for w in (True,False):
        X=[x for x in res if x[0]==w]
        print('won' if w else 'lost',len(X),'prism gems at end mean %.0f; max bag in game median %.0f; our score %.0f their %.0f; games where our score+prism end bag>=1000: %d'%(st.mean(x[1] for x in X),st.median(x[2] for x in X),st.mean(x[3] for x in X),st.mean(x[4] for x in X),sum(x[1]+x[3]>=1000 for x in X)))
