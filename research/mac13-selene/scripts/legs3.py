import json, gzip, sys, os, re, zipfile
from collections import deque, Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
AN='/home/ubuntu/wt/mac13-selene/replays/.analysis'
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        src=meta['source']
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        z=zipfile.ZipFile(src)
    except Exception as e: return None
    Dl={}
    for nm in z.namelist():
        if nm.endswith('.stdout'):
            for m in D_RE.finditer(z.read(nm)): Dl[(int(m.group(1)),int(m.group(2)))]=(m.group(3).decode(),int(m.group(4)))
    W,H=mp['width'],mp['height']
    block=set(map(tuple,mp['walls']))|set(map(tuple,mp['holes']))|set(map(tuple,mp['altars']))
    for c in mp['camps']: block.add((c['x'],c['y']))
    cache={}
    def bfs(s):
        if s in cache: return cache[s]
        Dd={s:0}; q=deque([s])
        while q:
            x,y=q.popleft()
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    p=(x+dx,y+dy)
                    if 0<=p[0]<W and 0<=p[1]<H and p not in block and p not in Dd: Dd[p]=Dd[(x,y)]+1; q.append(p)
        cache[s]=Dd; return Dd
    res=Counter(); n=len(R['round']); rounds=R['round']
    for c in R['champions']:
        i=1
        while i<n:
            if c['alive'][i] and c['alive'][i-1] and c['x'][i] is not None and c['x'][i-1] is not None and (c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1]):
                j=i
                while j+1<n and c['alive'][j+1] and c['x'][j+1] is not None and (c['x'][j+1],c['y'][j+1])!=(c['x'][j],c['y'][j]): j+=1
                steps=j-i+1
                if steps>=12 and not any(c['sees'][k] for k in range(i,j+1)) and len(cache)<300:
                    a=(c['x'][i-1],c['y'][i-1]); b=(c['x'][j],c['y'][j]); bd=bfs(a).get(b)
                    if bd is not None:
                        brs=[Dl.get((rounds[k],c['id'])) for k in range(i,j+1)]
                        brs=[x for x in brs if x]
                        fgs=[x[1] for x in brs if x[0]=='F']
                        nfg=len(set(fgs)); bset=''.join(sorted(set(x[0] for x in brs)))
                        waste=steps-bd
                        key=('multi_target' if nfg>1 else 'one_target') + '|' + ('F-only' if bset=='F' else bset[:6])
                        res[key+'#steps']+=steps; res[key+'#waste']+=waste; res[key+'#legs']+=1
                i=j+1
            else: i+=1
    return res
def main():
    idx=json.load(open(os.path.join(AN,'index.json')))
    dirs=[os.path.join(AN,g['dir']) for g in idx['games'] if 'mirdbg' in g['source']][:300]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=2):
            if r: tot.update(r)
    keys=sorted(set(k.split('#')[0] for k in tot), key=lambda k:-tot[k+'#waste'])
    for k in keys[:20]: print(f"{k:30s} legs {tot[k+'#legs']:6d} steps {tot[k+'#steps']:7d} waste {tot[k+'#waste']:7d}")
if __name__=='__main__': main()
