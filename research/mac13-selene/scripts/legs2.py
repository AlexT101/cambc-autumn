import json, gzip, sys, os
from collections import deque, Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
    except Exception: return None
    W,H=mp['width'],mp['height']
    block=set(map(tuple,mp['walls']))|set(map(tuple,mp['holes']))|set(map(tuple,mp['altars']))
    for c in mp['camps']: block.add((c['x'],c['y']))
    cache={}
    def bfs(s):
        if s in cache: return cache[s]
        D={s:0}; q=deque([s])
        while q:
            x,y=q.popleft()
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    p=(x+dx,y+dy)
                    if 0<=p[0]<W and 0<=p[1]<H and p not in block and p not in D:
                        D[p]=D[(x,y)]+1; q.append(p)
        cache[s]=D; return D
    res=Counter()
    n=len(R['round'])
    for c in R['champions'][:]:
        i=1
        while i<n:
            if c['alive'][i] and c['alive'][i-1] and c['x'][i] is not None and c['x'][i-1] is not None and (c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1]):
                j=i
                while j+1<n and c['alive'][j+1] and c['x'][j+1] is not None and (c['x'][j+1],c['y'][j+1])!=(c['x'][j],c['y'][j]): j+=1
                a=(c['x'][i-1],c['y'][i-1]); b=(c['x'][j],c['y'][j]); steps=j-i+1
                if steps>=4 and len(cache)<400:
                    D=bfs(a); bd=D.get(b)
                    if bd is not None and bd<=steps:
                        cheb=max(abs(a[0]-b[0]),abs(a[1]-b[1]))
                        seen=any(c['sees'][k] for k in range(i,j+1))
                        key='seen' if seen else 'quiet'
                        L=steps
                        lb='4-8' if L<=8 else ('9-16' if L<=16 else '17+')
                        for kk in (key, key+lb):
                            res[kk+'_steps']+=steps; res[kk+'_bfs']+=bd; res[kk+'_legs']+=1
                i=j+1
            else: i+=1
    return res
def main():
    dirs=sorted([os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps'])[:200]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=2):
            if r: tot.update(r)
    for k in sorted(set(x.rsplit('_',1)[0] for x in tot)):
        print(f"{k:12s} legs {tot[k+'_legs']:7d} steps {tot[k+'_steps']:8d} steps/bfs {tot[k+'_steps']/max(1,tot[k+'_bfs']):.2f}")
if __name__=='__main__': main()
