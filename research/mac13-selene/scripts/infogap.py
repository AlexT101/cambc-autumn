import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}
    team={c['id']:c['team'] for c in meta['champions']}
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}
    rix={r:i for i,r in enumerate(R['round'])}
    out=[]
    for e in ev:
        if e['k']!='death' or e.get('by') is None or e.get('linked'): continue
        v=e['v']; k=e['by']; r=e['r']
        if k not in idx: continue
        i=rix.get(r)
        if i is None: continue
        vic=ch[idx[v]]
        self_seen=[k in (vic['sees'][j] or []) for j in range(max(0,i-6),i)]
        ally_seen=False
        for c in ch:
            if c['team']==team[v] and c['id']!=v:
                for j in range(max(0,i-6),i):
                    if k in (c['sees'][j] or []): ally_seen=True
        out.append((names[v], names[k], e.get('gems',0), any(self_seen[-1:]), any(self_seen), ally_seen))
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    print('kills',len(rows))
    c=Counter((a,b,cc) for _,_,_,a,b,cc in rows)
    print('(victim saw killer last round, victim saw killer in last 6 rounds, an ally saw killer in last 6)')
    for kk,v in c.most_common(): print(kk,v)
    pr=[x for x in rows if x[1]=='Prism']
    c=Counter((a,b,cc) for _,_,_,a,b,cc in pr); print('killer Prism'); [print(kk,v) for kk,v in c.most_common()]
if __name__=='__main__': main()
