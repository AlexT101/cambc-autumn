"""Gold by champion type: earned and unspent at r150/300/600, max HP, str, focus; mirror both teams."""
import gzip, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
CH=(150,300,600)
def one(d):
    d=Path(d)
    try:
        meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    except Exception: return None
    typ={c['id']:c['name'] for c in meta['champions']}
    out=defaultdict(list)
    n=len(R['round'])
    for c in R['champions']:
        t=typ[c['id']]
        for r in CH:
            if r>n: continue
            ix=r-1
            out[(t,r,'earned')].append(c['earned'][ix]); out[(t,r,'unspent')].append(c['gold'][ix])
            out[(t,r,'maxhp')].append(c['maxHp'][ix]); out[(t,r,'str')].append(c['str'][ix]); out[(t,r,'foc')].append(c['foc'][ix])
            out[(t,r,'alive')].append(c['alive'][ix])
    return out
if __name__=='__main__':
    dirs=[str(p.parent) for p in Path(sys.argv[1]).glob('*/meta.json')]
    tot=defaultdict(list)
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one,dirs,chunksize=8):
            if r:
                for k,v in r.items(): tot[k]+=v
    types=sorted(set(k[0] for k in tot))
    for t in types:
        n=len(tot[(t,300,'earned')])
        row=[]
        for r in CH:
            e=tot[(t,r,'earned')]
            if not e: continue
            m=lambda k: sum(tot[(t,r,k)])/len(tot[(t,r,k)])
            row.append(f"r{r}: earn {m('earned'):6.0f} unsp {m('unspent'):5.0f} hp {m('maxhp'):5.0f} str {m('str'):5.1f} foc {m('foc'):5.0f}")
        print(f"{t:14s} n={n:5d} | "+" | ".join(row))
