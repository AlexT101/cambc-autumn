import sys; sys.path.insert(0,sys.argv[1])
from tlib import *
from concurrent.futures import ProcessPoolExecutor
def one(kv):
    key,v=kv
    T,TV=load(key); o=Counter(); ex=[]
    byc=defaultdict(dict)
    for (r,c),L in T.items():
        if L['TT'] and c in TV: byc[c][r]=L
    for c,R in byc.items():
        rs=sorted(R)
        for r in rs:
            if r-1 not in R or r-2 not in R: continue
            a,b,cc=R[r-2]['TT'][0],R[r-1]['TT'][0],R[r]['TT'][0]
            if a.get('a')!='1' or b.get('a')!='1' or cc.get('a')!='1': continue
            o['turns']+=1
            # A-B-A: end pos at r == end pos at r-2, differs from r-1
            if cc.get('q')==a.get('q') and b.get('q')!=a.get('q'):
                o['aba']+=1
                pair=''.join(sorted([b.get('d','?'),cc.get('d','?')]))
                o[('pair',pair)]+=1
                hw=[e.get('why') for e in R[r]['TE'] if e.get('k')=='home']+[e.get('why') for e in R[r-1]['TE'] if e.get('k')=='home']
                o[('why',tuple(sorted(set(x for x in hw if x))))]+=1
                o[('type',TV[c]['t'])]+=1
                if len(ex)<4 and pair in('FR','PR','BR'): ex.append((key,r,c,TV[c]['t'],b.get('d'),cc.get('d'),a.get('q'),b.get('q'),cc['hp'],hw))
    return o,ex
if __name__=='__main__':
    K=keys()
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,K))
    T=Counter(); E=[]
    for o,e in res: T.update(o); E+=e
    print('games',len(K),'champion turns',T['turns'],'A-B-A turns',T['aba'],'%.3f'%(T['aba']/T['turns']))
    print('branch pairs',[(k[1],v) for k,v in T.most_common() if k[0]=='pair'][:12])
    print('home why',[(k[1],v) for k,v in T.most_common() if k[0]=='why'][:12])
    print('types',[(k[1],v) for k,v in T.most_common() if k[0]=='type'][:12])
    for e in E[:16]: print(e)
