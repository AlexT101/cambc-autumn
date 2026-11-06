import json,gzip,sys,collections,statistics
ana=sys.argv[1]; names=json.load(open(sys.argv[2])); geo={}
ix=json.load(open(f'{ana}/index.json'))['games']; seen=set()
rows=[]
for x in ix:
    d=x['dir']
    if d in seen: continue
    seen.add(d)
    m=json.load(open(f'{ana}/{d}/meta.json')); R=json.load(gzip.open(f'{ana}/{d}/rounds.json.gz'))
    mp=json.load(open(f"{ana}/maps/{m['map']['hash']}.json")); na=len(mp['altars'])
    # zones by chebyshev<=10
    al=mp['altars']; z=list(range(na))
    def f(i):
        while z[i]!=i: i=z[i]
        return i
    for i in range(na):
        for j in range(i+1,na):
            if max(abs(al[i][0]-al[j][0]),abs(al[i][1]-al[j][1]))<=10: z[f(i)]=f(j)
    nz=len({f(i) for i in range(na)})
    N=len(R['round'])
    for t in (0,1):
        cs=[c for c in R['champions'] if c['team']==t]
        ready=None
        for i in range(N):
            sc=R['gems'][t][i]
            if sc>=1000: break
            if any(sc+(c['gems'][i] or 0)>=1000 for c in cs): ready=i; break
        if ready is None: continue
        won=m['result']['winner']==t
        end=next((i for i in range(ready,N) if R['gems'][t][i]>=1000),None)
        rows.append(dict(who=names.get(d,['?','?'])[t], nz=nz, won=won, delay=(R['round'][end]-R['round'][ready]) if end is not None else None, r=R['round'][ready]))
c=collections.defaultdict(list)
for r in rows: c[(r['who'] if r['who'] in ('astraeus','ocean','Pantheon') else 'others','1zone' if r['nz']==1 else 'multi')].append(r)
for k,v in sorted(c.items()):
    dl=[r['delay'] for r in v if r['delay'] is not None]
    print(k,'sides',len(v),'won%',round(100*sum(r['won'] for r in v)/len(v),1),'median delay',statistics.median(dl) if dl else None,'p75',sorted(dl)[int(.75*len(dl))] if dl else None, 'delay>30 %', round(100*sum(x>30 for x in dl)/max(1,len(dl))))
