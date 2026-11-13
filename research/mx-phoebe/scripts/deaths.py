"""Deaths per team-game by type (W/L), killer type, and r<=400 share; maxHp at death vs killer Focus for Cassi/Willow."""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    d=Path(d)
    try:
        meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
        ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    except Exception: return None
    typ={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    idx={c['id']:i for i,c in enumerate(R['champions'])}
    w=meta['result']['winner']; out=Counter()
    for e in ev:
        if e['k']!='death' or e.get('linked'): continue
        v=e['v']; side='W' if team[v]==w else 'L'
        t=typ[v]; t='C&I' if t in ('Cassi','Issac') else t
        out[(side,t)]+=1
        if e['r']<=400: out[(side,t,'r400')]+=1
        k=e.get('by'); kt=typ.get(k,'camp') if k is not None else 'camp'
        out[(side,'killer',kt)]+=1
        ix=max(0,e['r']-2); c=R['champions'][idx[v]]
        if t in ('C&I','Willow','Prism') and k in typ:
            kc=R['champions'][idx[k]]
            if typ[k]=='Prism':
                ratio=c['maxHp'][ix]/(1.5*kc['foc'][ix]+1)
                b='<1' if ratio<1 else '1-1.5' if ratio<1.5 else '1.5+'
                out[(side,t,'vsPrism',b)]+=1
    out[('W','games')]+=1; out[('L','games')]+=1
    return out
if __name__=='__main__':
    dirs=[str(p.parent) for p in Path(sys.argv[1]).glob('*/meta.json')]
    tot=Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one,dirs,chunksize=8):
            if r: tot.update(r)
    n=tot[('W','games')]
    for k,v in sorted(tot.items(), key=lambda kv: (str(kv[0][1:]),kv[0][0])):
        print(k, round(v/n,3))
