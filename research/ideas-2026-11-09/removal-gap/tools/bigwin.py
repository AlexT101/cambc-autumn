import beh, json, sys, os, collections
from multiprocessing import Pool
import lockcut_run as L
def run(j):
    k,d,T=j
    try: meta,rd,ev=beh.load(d)
    except Exception: return (k,[])
    team={c['id']:c['team'] for c in meta['champions']}
    rounds=rd['round']; out=[]
    for e in ev:
        if e['k']=='tribute_start' and e['gems']>=150:
            t=team[e['a']]; i=min(len(rounds)-1,max(0,e['r']-1))
            score=rd['gems'][t][i]
            out.append(('us' if t==T else 'op', e['gems'], score, int(score+e['gems']>=1000), e['r']))
    return (k,out)
if __name__=='__main__':
    jobs=L.jl()+L.jloc(sys.argv[1],1)
    with Pool(32) as p: res=p.map(run,jobs,chunksize=8)
    G=collections.defaultdict(list)
    for k,o in res:
        for x in o: G[(k,x[0])].append(x)
    import statistics as st
    for (k,s),L2 in sorted(G.items()):
        b3=[x for x in L2 if x[1]>=300]
        print(f'{k:14} {s} 150+ starts {len(L2)}: winning {st.mean(x[3] for x in L2):.2f}, med round {st.median(x[4] for x in L2)}; 300+: {len(b3)} winning {st.mean(x[3] for x in b3) if b3 else 0:.2f} med score before {st.median(x[2] for x in b3) if b3 else 0}')
