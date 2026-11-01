import sys; sys.path.insert(0,sys.argv[1])
import ranged as rg
from common import *
from concurrent.futures import ProcessPoolExecutor
if __name__=='__main__':
    G=games()
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(rg.one,G))
    pm=defaultdict(Counter)
    for g,o in zip(G,res):
        for k,v in o.items():
            if len(k)==3 and k[1]=='ALL': pm[g['map']][(k[0],k[2])]+=v
    worse=0;tot=0;rows=[]
    for mname,c in pm.items():
        nu=sum(c[('us',x)] for x in ('hit','move','camp','none')); nt=sum(c[('them',x)] for x in ('hit','move','camp','none'))
        if nu<30 or nt<30: continue
        hu=c[('us','hit')]/nu; ht=c[('them','hit')]/nt; tot+=1; worse+= hu<ht; rows.append((round(hu-ht,2),mname))
    print('maps with >=30 turns each side:',tot,'maps where our ranged hit rate is lower:',worse)
    print('closest/better maps',sorted(rows)[-5:])
