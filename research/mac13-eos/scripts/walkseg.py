"""Walking in a window: share of alive rounds walking, split by where the walk started (spawn, camp work, hold, fight).
LO HI env. py walkseg.py EXTRACT_DIR"""
import gzip,json,sys,collections,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
LO=int(os.environ.get('LO','1')); HI=int(os.environ.get('HI','99999'))
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    act=collections.defaultdict(set)
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k'] in ('attack','cast') and e.get('a') is not None: act[e['a']].add(e['r'])
    gt=set(tuple(t) for x in mp['groups'] for t in x['tiles'])
    out=collections.Counter(); n=len(R['round'])
    for c in R['champions']:
        cid=int(c['id']); s=mp['spawn'][int(c['team'])]
        start='start'; 
        for i in range(1,min(n,HI)):
            r=i+1
            if not c['alive'][i]: start='dead'; continue
            on=s['minX']<=c['x'][i]<=s['maxX'] and s['minY']<=c['y'][i]<=s['maxY']
            moved=(c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1]) and c['alive'][i-1]
            if r in act[cid]: k='work'; start='work'
            elif on: k='spawn'; start='spawn'
            elif moved: k='walk:'+start
            elif (c['x'][i],c['y'][i]) in gt: k='hold'; start='hold'
            else: k='still'
            if r>=LO: out[k]+=1
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    T=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(g,dirs,chunksize=8): T.update(r)
    S=sum(T.values())
    for k,v in T.most_common(): print(f'{k:14s} {v/S:.3f}')
