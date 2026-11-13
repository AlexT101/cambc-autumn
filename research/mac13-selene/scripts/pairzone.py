import json, gzip, sys, os
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
exec(open('/tmp/selene/hazard.py').read().split('def game')[0].split("ROOT=sys.argv[1]")[1])
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    Ds=[bfs(mp,mp['spawn'][0]),bfs(mp,mp['spawn'][1])]
    cn={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}; rix={r:i for i,r in enumerate(R['round'])}
    res=Counter()
    for e in ev:
        if e['k']=='death' and not e.get('linked') and cn[e['v']] in ('Cassi','Issac'):
            c=ch[idx[e['v']]]; i=rix.get(e['r']-1,0); x,y=c['x'][i],c['y'][i]
            if x is None: continue
            t=team[e['v']]; a=Ds[t][x][y]; b=Ds[1-t][x][y]
            if max(a,b)>10**8: continue
            s=a/(a+b) if a+b else .5
            z='own' if s<.4 else 'mid' if s<=.6 else 'enemy'
            p=[o for o in ch if o['team']==t and cn[o['id']] in('Cassi','Issac') and o['id']!=e['v']]
            far='?'
            if p and p[0]['x'][i] is not None: far='near' if max(abs(p[0]['x'][i]-x),abs(p[0]['y'][i]-y))<=6 else 'far'
            res[(z,far)]+=1
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    print(sorted(tot.items()))
if __name__=='__main__': main()
