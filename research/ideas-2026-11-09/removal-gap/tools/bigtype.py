import beh, json, sys, os, collections
from multiprocessing import Pool
import lockcut_run as L
def run(j):
    k,d,T=j
    try: meta,rd,ev=beh.load(d)
    except Exception: return (k,[])
    team={c['id']:c['team'] for c in meta['champions']}; name={c['id']:c['name'] for c in meta['champions']}
    rounds=rd['round']; out=[]
    for e in ev:
        if e['k']=='tribute_start' and e['gems']>=200:
            t=team[e['a']]; i=min(len(rounds)-1,max(0,e['r']-1)); score=rd['gems'][t][i]
            out.append(('us' if t==T else 'op', name[e['a']], e['gems'], e['dur'], int(score+e['gems']>=1000)))
    return (k,out)
if __name__=='__main__':
    jobs=L.jl()+L.jloc(sys.argv[1],1)
    with Pool(32) as p: res=p.map(run,jobs,chunksize=8)
    G=collections.defaultdict(list); n=collections.Counter()
    for k,o in res:
        n[k]+=1
        for x in o: G[(k,x[0])].append(x)
    import statistics as st
    for (k,s),X in sorted(G.items()):
        c=collections.Counter(x[1] for x in X); w=[x for x in X if x[4]]
        print(f'{k:14} {s} 200+ starts/g {len(X)/n[k]:.2f} winning/g {len(w)/n[k]:.2f} win-dur med {st.median(x[3] for x in w) if w else 0} gems med {st.median(x[2] for x in w) if w else 0} | top types', c.most_common(5))
