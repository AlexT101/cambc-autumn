import json, gzip, sys, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def bfs_side(mp):
    from collections import deque
    W,H=mp['width'],mp['height']
    block=set(map(tuple,mp['walls']))|set(map(tuple,mp['holes']))|set(map(tuple,mp['altars']))
    res=[]
    for s in mp['spawn']:
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
        res.append(D)
    return res
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}
    team={c['id']:c['team'] for c in meta['champions']}
    prisms=[c['id'] for c in meta['champions'] if c['name']=='Prism']
    if len(prisms)!=2: return None
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}
    rix={r:i for i,r in enumerate(R['round'])}
    D=bfs_side(mp)
    win=meta['result']['winner']
    for e in ev:
        if e['k']=='death' and e['v'] in prisms:
            v=e['v']; t=team[v]; r=e['r']; i=rix.get(r-1,0)
            c=ch[idx[v]]; x,y=c['x'][i],c['y'][i]
            if x is None: return None
            dO=D[t][x][y]; dE=D[1-t][x][y]; share=dO/(dO+dE) if dO+dE>0 else .5
            zone='own' if share<.4 else ('mid' if share<=.6 else 'enemy')
            other=[p for p in prisms if p!=v][0]; oc=ch[idx[other]]
            ratio=(c['gems'][i]+1)/(oc['gems'][i]+1) if oc['alive'][i] else 9
            a6=sum(1 for cc in ch if cc['team']==t and cc['id']!=v and cc['alive'][i] and cc['x'][i] is not None and max(abs(cc['x'][i]-x),abs(cc['y'][i]-y))<=6)
            k6=sum(1 for cc in ch if cc['team']!=t and cc['alive'][i] and cc['x'][i] is not None and max(abs(cc['x'][i]-x),abs(cc['y'][i]-y))<=6)
            killer=names.get(e.get('by'),'camp')
            return dict(zone=zone, ratio=ratio, a6=a6, k6=k6, killer=killer, vwin=int(t==win), r=r, gems=e.get('gems',0))
    return dict(none=1)
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows.append(r)
    fr=[r for r in rows if 'zone' in r]
    print('games with 2 prisms',len(rows),'first prism death',len(fr),'victim team wins',sum(r['vwin'] for r in fr)/len(fr))
    print('zone',Counter(r['zone'] for r in fr)); print('killer',Counter(r['killer'] for r in fr).most_common(6))
    print('bag ratio victim/other: <0.67',sum(r['ratio']<0.67 for r in fr),' 0.67-1.5',sum(0.67<=r['ratio']<=1.5 for r in fr),' >1.5',sum(r['ratio']>1.5 for r in fr))
    print('allies within 6 of victim vs enemies within 6', Counter((min(r['a6'],3),min(r['k6'],4)) for r in fr).most_common(12))
    import statistics as st; print('median round', st.median(r['r'] for r in fr), 'mean gems', st.mean(r['gems'] for r in fr))
if __name__=='__main__': main()
