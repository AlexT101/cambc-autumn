import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    R=rounds(r['dir']); us=r['us']; o={}
    for rn in (200,400,600):
        if rn>len(R['round']): continue
        i=rn-1
        for s,t in (('us',us),('them',1-us)):
            cs=[c for c in R['champions'] if c['team']==t]
            o[(s,rn,'unspent')]=sum(c['gold'][i] for c in cs); o[(s,rn,'earned')]=sum(c['earned'][i] for c in cs)
            o[(s,rn,'maxchamp_mh')]=max(c['maxHp'][i] for c in cs); o[(s,rn,'maxfoc')]=max(c['foc'][i] for c in cs)
    return o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,games()))
    for rn in (200,400,600):
        for k in ('earned','unspent','maxchamp_mh','maxfoc'):
            X=[o for o in res if ('us',rn,k) in o]
            print(rn,k,'us %.0f them %.0f'%(sum(o[('us',rn,k)] for o in X)/len(X),sum(o[('them',rn,k)] for o in X)/len(X)))
