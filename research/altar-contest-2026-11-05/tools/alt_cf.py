import json,gzip,sys,collections
sys.argv=[sys.argv[0]]+sys.argv[1:]
exec(open(sys.argv[1]).read().split("out = open(args.out, 'w')")[0].replace("args = ap.parse_args()","args = ap.parse_args(['x','--out','/dev/null'])"))
ana='replays/bush-ladder/analysis'
rows=[json.loads(l) for l in open(sys.argv[2])]
names=json.load(open(sys.argv[3]))
T=[r for r in rows if r['kind']=='trib' and r['dur']>=9 and r['nz']>=2]
by=collections.defaultdict(list)
for r in T: by[r['d']].append(r)
c=collections.Counter(); ex=[]
for d,rs in by.items():
    m=json.load(open(f'{ana}/{d}/meta.json')); R=json.load(gzip.open(f'{ana}/{d}/rounds.json.gz')); ev=[json.loads(l) for l in gzip.open(f'{ana}/{d}/events.jsonl.gz','rt')]
    g=geom(ana,m['map']['hash']); W,H=g['W'],g['H']
    mm=json.load(open(f"{ana}/maps/{m['map']['hash']}.json"))
    block=[0]*(W*H)
    for k in ('walls','holes','altars'):
        for x,y in mm[k]: block[y*W+x]=1
    ri={r:i for i,r in enumerate(R['round'])}
    starts={(e['a'],e['r']):e for e in ev if e['k']=='tribute_start'}
    for r in rs:
        e=next((v for (a,rr),v in starts.items() if rr==r['r'] and v['gems']==r['gems']),None)
        if not e: continue
        a=e['a']; ch=next(c_ for c_ in R['champions'] if c_['id']==a)
        i0=ri.get(r['r']-12); i1=ri.get(r['r']-1)
        if i0 is None or not ch['alive'][i0] or ch['x'][i0] is None: continue
        f=bfs(W,H,block,[(ch['x'][i0],ch['y'][i0])])
        def tw(k):
            ax,ay=g['alts'][k]; return min([f[(ay+dy)*W+ax+dx] for dx in(-1,0,1) for dy in(-1,0,1) if 0<=ax+dx<W and 0<=ay+dy<H and not block[(ay+dy)*W+ax+dx]]+[1<<20])
        used=r['alt']; wu=tw(used)
        t=r['team']
        def en8(k,i):
            p=g['alts'][k]; return sum(1 for c_ in R['champions'] if c_['team']!=t and c_['alive'][i] and c_['x'][i] is not None and max(abs(c_['x'][i]-p[0]),abs(c_['y'][i]-p[1]))<=8)
        enu=en8(used,i1)
        best=None
        for k in range(g['n']):
            if g['zones'][k]==g['zones'][used]: continue
            extra=tw(k)-wu
            if extra>15: continue
            e8=en8(k,i1)
            cand=(e8,extra,k)
            if best is None or cand<best: best=cand
        who=names.get(d,['?','?'])[t]
        key=('enemy@used' if enu else 'clear@used', 'no alt<=15' if best is None else ('alt clear' if best[0]==0 else 'alt busy'), r['res']=='end')
        c[key]+=1
        if best and best[0]==0 and enu: ex.append(best[1])
for k in sorted(c): print(k,c[k])
import statistics
if ex: print('extra steps to a clear other-zone altar when used one had an enemy:',len(ex),'median',statistics.median(ex), 'share<=5',sum(x<=5 for x in ex)/len(ex))
