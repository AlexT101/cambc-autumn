import json, gzip, sys, os
from collections import defaultdict, Counter, deque
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
    DA=bfs(mp,mp['spawn'][0]); DB=bfs(mp,mp['spawn'][1])
    side={}
    for g in mp['groups']:
        a=min(DA[t[0]][t[1]] for t in g['tiles']); b=min(DB[t[0]][t[1]] for t in g['tiles'])
        side[g['id']]=a/(a+b) if a+b>0 and max(a,b)<10**8 else .5
    ch=R['champions']; rix={r:i for i,r in enumerate(R['round'])}
    n=len(R['round'])
    dead=[[0]*n,[0]*n]
    for c in ch:
        for i in range(n):
            if not c['alive'][i]: dead[c['team']][i]+=1
    res=Counter()
    # rounds by enemy-dead count, per team
    for t in (0,1):
        for i in range(n): res[(t,'rounds',min(dead[1-t][i],3))]+=1
    for e in ev:
        if e['k']=='capture':
            t=e['team']; s=side[e['g']]; s=s if t==0 else 1-s
            z='own' if s<.4 else ('mid' if s<=.6 else 'enemy')
            i=rix.get(e['r'],n-1); k=min(dead[1-t][i],3)
            res[(t,z,k)]+=sum(x[1] for x in e['shares'])
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    for k in range(4):
        rounds=tot[(0,'rounds',k)]+tot[(1,'rounds',k)]
        line=f"enemy dead {k}: share of rounds {rounds/sum(tot[(t,'rounds',j)] for t in (0,1) for j in range(4)):.3f}"
        for z in ('own','mid','enemy'):
            g=tot[(0,z,k)]+tot[(1,z,k)]; line+=f"  {z} gems/100 rounds {100*g/rounds:.2f}"
        print(line)
if __name__=='__main__': main()
