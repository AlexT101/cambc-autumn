import beh, json, sys, os, collections, statistics as st
from multiprocessing import Pool
import lockcut_run as L
def run(j):
    k,d,T=j
    try: meta,rd,ev=beh.load(d)
    except Exception: return (k,None)
    team={c['id']:c['team'] for c in meta['champions']}
    ri={r:i for i,r in enumerate(rd['round'])}; ch={c['id']:c for c in rd['champions']}
    out=collections.Counter(); firsts=[]
    seen=set()
    for e in ev:
        if e['k']=='shop':
            n=sum(v for it,v in (e.get('items') or {}).items() if it.startswith('Tribute') and v>0)
            if n>0:
                side='T' if team[e['a']]==T else 'V'; out[f'trib_shards_{side}']+=n
                if (e['a']) not in seen:
                    seen.add(e['a']); ix=ri.get(e['r'])
                    g=ch[e['a']]['gems'][ix] if ix is not None else -1
                    out[f'buyers_{side}']+=1
                    out[f'buyer_bag_{side}_{"<100" if g<100 else "100-137" if g<138 else "138+"}']+=1
    return (k,out)
if __name__=='__main__':
    jobs=[]
    if '--live' in sys.argv: jobs+=L.jl()
    for a in sys.argv[1:]:
        if a.startswith('--'): continue
        p,b=a.rsplit(':',1); jobs+=[(os.path.basename(p)+f'-T{b}',d,T) for _,d,T in L.jloc(p,int(b))]
    with Pool(32) as pool: res=pool.map(run,jobs,chunksize=8)
    G=collections.defaultdict(collections.Counter); n=collections.Counter()
    for k,o in res:
        if o is not None: G[k].update(o); n[k]+=1
    for k in sorted(G): print(k, {x:round(v/n[k],3) for x,v in sorted(G[k].items())})
