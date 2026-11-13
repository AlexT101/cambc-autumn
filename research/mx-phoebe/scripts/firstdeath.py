"""First champion death of each game: victim type, killer type, round bucket; the victim team's win rate after."""
import gzip, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    d=Path(d)
    try:
        meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
        ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    except Exception: return None
    typ={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    idx={c['id']:i for i,c in enumerate(R['champions'])}
    w=meta['result']['winner']
    for e in ev:
        if e['k']=='death' and not e.get('linked') and e.get('by') in typ:
            v=e['v']; t=typ[v]; t='C&I' if t in ('Cassi','Issac') else t
            kt=typ[e['by']]
            ix=max(0,e['r']-2)
            # victim's own Prism distance
            pr=[c for c in typ if typ[c]=='Prism' and team[c]==team[v] and c!=v]
            vp=(R['champions'][idx[v]]['x'][ix],R['champions'][idx[v]]['y'][ix])
            pd=None
            if pr:
                c=R['champions'][idx[pr[0]]]
                if c['alive'][ix] and c['x'][ix] is not None: pd=cheb(vp,(c['x'][ix],c['y'][ix]))
            # allies/enemies within 8
            na=ne=0
            for cid in typ:
                c=R['champions'][idx[cid]]
                if cid==v or not c['alive'][ix] or c['x'][ix] is None: continue
                if cheb(vp,(c['x'][ix],c['y'][ix]))<=8:
                    if team[cid]==team[v]: na+=1
                    else: ne+=1
            return (t,kt,e['r'],1 if team[v]==w else 0,pd,na,ne,e.get('gems',0))
    return ('none',)
if __name__=='__main__':
    dirs=[str(p.parent) for p in Path(sys.argv[1]).glob('*/meta.json')]
    rs=[]
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one,dirs,chunksize=8):
            if r: rs.append(r)
    print(len(rs),'games; no kill:',sum(1 for r in rs if r[0]=='none'))
    rs=[r for r in rs if r[0]!='none']
    c=Counter((r[0]) for r in rs); 
    for t,n in c.most_common():
        sub=[r for r in rs if r[0]==t]
        print(f"victim {t:12s} n={n:4d} victim-team win {100*sum(r[3] for r in sub)/n:5.1f}%  median r {sorted(r[2] for r in sub)[n//2]}  killers {Counter(r[1] for r in sub).most_common(3)}  ownPrism<=6 {sum(1 for r in sub if r[4] is not None and r[4]<=6)/n:.2f}  allies8 {sum(r[5] for r in sub)/n:.2f} enemies8 {sum(r[6] for r in sub)/n:.2f} bag {sum(r[7] for r in sub)/n:.0f}")
