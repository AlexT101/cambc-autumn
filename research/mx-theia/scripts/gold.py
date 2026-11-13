# Mean unspent gold and earned gold by type at rounds; max HP and str/focus.
import json,gzip,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx=json.load(open(ROOT+'/index.json'))
dirs=sorted(set(g['dir'] for g in idx['games']))
RS=(100,200,300,450,600)
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    typ={c['id']:en[c['type']] for c in meta['champions']}
    out=collections.defaultdict(list); n=len(R['round'])
    for c in R['champions']:
        t=typ[c['id']]
        for r in RS:
            if n>=r:
                i=r-1
                out[(t,r,'gold')].append(c['gold'][i] or 0); out[(t,r,'earned')].append(c['earned'][i] or 0)
                out[(t,r,'maxHp')].append(c['maxHp'][i] or 0); out[(t,r,'str')].append(c['str'][i] or 0); out[(t,r,'foc')].append(c['foc'][i] or 0)
        # time-average unspent gold r1-600
        g=[c['gold'][i] or 0 for i in range(min(n,600))]
        out[(t,0,'avg_unspent')].append(sum(g)/len(g))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,dirs,chunksize=4) if r]
    A=collections.defaultdict(list)
    for o in res:
        for k,v in o.items(): A[k]+=v
    types=sorted(set(k[0] for k in A))
    for t in types:
        s=f"{t:14s} avgUnspent {statistics.mean(A[(t,0,'avg_unspent')]):5.0f} |"
        for r in RS:
            if A[(t,r,'gold')]: s+=f" r{r}: g{statistics.mean(A[(t,r,'gold')]):.0f} e{statistics.mean(A[(t,r,'earned')]):.0f} hp{statistics.mean(A[(t,r,'maxHp')]):.0f} s{statistics.mean(A[(t,r,'str')]):.0f} f{statistics.mean(A[(t,r,'foc')]):.0f} |"
        print(s)
