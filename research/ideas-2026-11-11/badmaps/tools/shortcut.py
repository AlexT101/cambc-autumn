import json,glob,os,sys,collections
from collections import deque
def analyse(mp):
    W,H=mp['width'],mp['height']
    blk=set(map(tuple,mp['walls']))|set(map(tuple,mp['holes']))|set(map(tuple,mp['altars']))
    INF=10**6
    def bfs(srcs):
        D={}
        q=deque()
        for s in srcs:
            if s not in D: D[s]=0;q.append(s)
        while q:
            x,y=q.popleft();d=D[(x,y)]
            for dx in(-1,0,1):
                for dy in(-1,0,1):
                    n=(x+dx,y+dy)
                    if (dx or dy) and 0<=n[0]<W and 0<=n[1]<H and n not in blk and n not in D:
                        D[n]=d+1;q.append(n)
        return D
    trib=set()
    for ax,ay in mp['altars']:
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                n=(ax+dx,ay+dy)
                if 0<=n[0]<W and 0<=n[1]<H and n not in blk: trib.add(n)
    D=bfs(trib)
    # hop value
    Hop={}
    for (x,y),d in D.items():
        best=INF
        for dx in range(-3,4):
            for dy in range(-3,4):
                v=D.get((x+dx,y+dy))
                if v is not None and v<best: best=v
        Hop[(x,y)]=best+3
    # D2: at most one hop: multi-source Dijkstra with seeds min(D,Hop) -> since unit steps, do bucketed relax
    D2={p:min(D[p],Hop[p]) for p in D}
    order=sorted(D2,key=lambda p:D2[p])
    import heapq
    pq=[(D2[p],p) for p in D2]; heapq.heapify(pq)
    while pq:
        d,(x,y)=heapq.heappop(pq)
        if d>D2[(x,y)]: continue
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                n=(x+dx,y+dy)
                if n in D2 and D2[n]>d+1: D2[n]=d+1; heapq.heappush(pq,(d+1,n))
    out={}
    for t,s in enumerate(mp['spawn']):
        c=((s['minX']+s['maxX'])//2,(s['minY']+s['maxY'])//2)
        out['spawn%d'%t]=(D.get(c,INF),D2.get(c,INF))
    # per gem group (own side of team 0): supply-weighted
    tot=0;wd=0;wd2=0;near=0
    for g in mp['groups']:
        if g['gems']<=0: continue
        w=g['gems']/g['respawn']
        ds=[];ds2=[]
        for tx,ty in g['tiles']:
            for dx in(-1,0,1):
                for dy in(-1,0,1):
                    n=(tx+dx,ty+dy)
                    if n in D: ds.append(D[n]);ds2.append(D2[n])
        if not ds: continue
        tot+=w;wd+=w*min(ds);wd2+=w*min(ds2);near+=w*(min(ds)<=5)
    out['camp_altar']=wd/max(tot,1e-9);out['camp_altar_hop']=wd2/max(tot,1e-9);out['near5_share']=near/max(tot,1e-9)
    out['naltars']=len(mp['altars']);out['size']=(W,H)
    return out
if __name__=='__main__':
    EXT='/home/ubuntu/tmp-offload/badmaps/ext'
    idx=json.load(open(EXT+'/index.json'))['games']
    names={g['mapHash']:g['map'] for g in idx}
    res={}
    for f in glob.glob(EXT+'/maps/*.json'):
        mp=json.load(open(f))
        nm=names.get(mp['hash'],mp['hash'][:8])
        res[nm]=analyse(mp)
    json.dump(res,open('shortcut-ladder.json','w'))
    rows=sorted(res.items(),key=lambda kv:-(kv[1]['spawn0'][0]-kv[1]['spawn0'][1]))
    print('maps',len(rows))
    print('map: spawn->altar walk / with one hop | gem-supply-weighted camp->altar walk / with hop | share of gem supply within 5 of an altar')
    for nm,r in rows[:22]:
        print(f"{nm:22s} {r['spawn0'][0]:3d} / {r['spawn0'][1]:3d} | {r['camp_altar']:5.1f} / {r['camp_altar_hop']:5.1f} | {r['near5_share']:.2f} altars {r['naltars']}")
    g8=sum(1 for _,r in rows if r['spawn0'][0]-r['spawn0'][1]>=8); g5=sum(1 for _,r in rows if r['spawn0'][0]-r['spawn0'][1]>=5)
    c5=sum(1 for _,r in rows if r['camp_altar']-r['camp_altar_hop']>=4)
    print('spawn gain>=8:',g8,'>=5:',g5,'camp-weighted gain>=4:',c5,'of',len(rows))
    import statistics as st
    print('near5_share quartiles',[round(x,2) for x in st.quantiles([r['near5_share'] for _,r in rows],n=4)],'camp_altar quartiles',[round(x,1) for x in st.quantiles([r['camp_altar'] for _,r in rows],n=4)])
    print('maps with near5_share>=0.5:',sorted(nm for nm,r in rows if r['near5_share']>=0.5))
