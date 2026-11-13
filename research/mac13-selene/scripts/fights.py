import json, gzip, sys, os
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
TYPES=None
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}; team={c['id']:c['team'] for c in ch}
    typ={c['id']:c['type'] for c in meta['champions']}
    rix={r:i for i,r in enumerate(R['round'])}
    out=[]
    win=meta['result']['winner']
    for e in ev:
        if e['k']!='death' or e.get('by') is None or e.get('linked'): continue
        v=e['v']; r=e['r']
        i=rix.get(r-1, rix.get(r))
        if i is None: continue
        vi=idx[v]; vx,vy=ch[vi]['x'][i],ch[vi]['y'][i]
        if vx is None: continue
        rec={'vtype':typ[v],'gems':e.get('gems',0),'vwin':int(team[v]==win),'r':r}
        for back in (0,5):
            j=max(0,i-back)
            px,py=ch[vi]['x'][j],ch[vi]['y'][j]
            if px is None: px,py=vx,vy
            for rad in (6,10,16):
                a=k=0
                for c in ch:
                    if c['id']==v or not c['alive'][j] or c['x'][j] is None: continue
                    if max(abs(c['x'][j]-px),abs(c['y'][j]-py))<=rad:
                        if c['team']==team[v]: a+=1
                        else: k+=1
                rec[f'a{rad}_{back}']=a; rec[f'k{rad}_{back}']=k
        out.append(rec)
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    print('kills',len(rows), 'per game', len(rows)/len(dirs))
    import statistics as st
    for back in (0,5):
      for rad in (6,10,16):
        a=st.mean(r[f'a{rad}_{back}'] for r in rows); k=st.mean(r[f'k{rad}_{back}'] for r in rows)
        print(f"back{back} r{rad}: victim allies {a:.2f}  killer side {k:.2f}")
    c=Counter((min(r['a10_5'],3),min(r['k10_5'],4)) for r in rows)
    print('victim-allies vs killers within 10, 5 rounds before:'); 
    for key in sorted(c): print(key,c[key])
    big=[r for r in rows if r['gems']>=100]
    print('100+ bag deaths',len(big),'victim allies r10 back5',st.mean(r['a10_5'] for r in big),'killers',st.mean(r['k10_5'] for r in big))
    print('types', Counter(r['vtype'] for r in rows))
if __name__=='__main__': main()
