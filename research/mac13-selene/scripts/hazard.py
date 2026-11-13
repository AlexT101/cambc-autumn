import json, gzip, sys, os
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def bfs(mp, s):
    W,H=mp['width'],mp['height']
    block=set(map(tuple,mp['walls']))|set(map(tuple,mp['holes']))|set(map(tuple,mp['altars']))
    D=[[10**9]*H for _ in range(W)]; q=deque()
    for x in range(s['minX'],s['maxX']+1):
        for y in range(s['minY'],s['maxY']+1): D[x][y]=0; q.append((x,y))
    while q:
        x,y=q.popleft()
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                nx,ny=x+dx,y+dy
                if 0<=nx<W and 0<=ny<H and (nx,ny) not in block and D[nx][ny]>D[x][y]+1:
                    D[nx][ny]=D[x][y]+1; q.append((nx,ny))
    return D
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    Ds=[bfs(mp,mp['spawn'][0]),bfs(mp,mp['spawn'][1])]
    ch=R['champions']; n=len(R['round']); rix={r:i for i,r in enumerate(R['round'])}
    cn={c['id']:c['name'] for c in meta['champions']}
    deaths=set()
    for e in ev:
        if e['k']=='death' and e.get('by') is not None and not e.get('linked'):
            deaths.add((e['v'], rix.get(e['r']-1,0)))
    res=Counter()
    for c in ch:
        t=c['team']
        for i in range(0,n,1):
            if not c['alive'][i] or c['x'][i] is None: continue
            x,y=c['x'][i],c['y'][i]
            a=Ds[t][x][y]; b=Ds[1-t][x][y]
            if a>10**8 or b>10**8: continue
            s=a/(a+b) if a+b else .5
            z='own' if s<.4 else 'mid' if s<=.6 else 'enemy'
            if s<0.15: z='home'
            na=0
            for o in ch:
                if o['team']==t and o['id']!=c['id'] and o['alive'][i] and o['x'][i] is not None and max(abs(o['x'][i]-x),abs(o['y'][i]-y))<=6: na+=1
            k=(z,min(na,3))
            res[k+('r',)]+=1
            if (c['id'],i) in deaths: res[k+('d',)]+=1
    return res
def main():
    dirs=sorted([os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps'])[:400]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: tot.update(r)
    for z in ('home','own','mid','enemy'):
        print(z, ' '.join(f"allies{k}: {1000*tot[(z,k,'d')]/max(1,tot[(z,k,'r')]):.2f}/1000r ({tot[(z,k,'r')]//1000}k)" for k in range(4)))
if __name__=='__main__': main()
