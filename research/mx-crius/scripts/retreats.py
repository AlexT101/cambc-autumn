"""Retreat episodes (runs of D-line branch R, mirror debug batch): how they end (death within the run + 3 rounds or
not), by HP at start, steps to own spawn at start (Chebyshev to the spawn centre), nearest ally, enemies within 6, and
whether the nearest ally lay closer than the spawn. usage: py retreats.py BATCH EXTRACT"""
import json,gzip,glob,os,sys,collections,re,zipfile
from concurrent.futures import ProcessPoolExecutor
B=sys.argv[1]; A=sys.argv[2]
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$',re.M)
idx={}
for g in json.load(open(A+'/index.json'))['games']: idx[os.path.basename(g['source'])]=g['dir']
def one(p):
    d=idx.get(os.path.basename(p))
    if not d: return []
    d=os.path.join(A,d)
    m=json.load(open(d+'/meta.json')); team={c['id']:c['team'] for c in m['champions']}
    mp=json.load(open(os.path.join(d,m['mapFile'])))
    sp={}
    for t,key in ((0,'spawnA'),(1,'spawnB')):
        pass
    br=collections.defaultdict(dict)
    z=zipfile.ZipFile(p)
    for n in z.namelist():
        if n.endswith('.stdout'):
            for x in D.finditer(z.read(n)): br[int(x.group(2))][int(x.group(1))]=x.group(3).decode()
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    ch={c['id']:c for c in R['champions']}
    # spawn centre: mean position at round 1
    i0=0
    cen={}
    for t in (0,1):
        xs=[(c['x'][i0],c['y'][i0]) for c in R['champions'] if c['team']==t and c['x'][i0] is not None]
        cen[t]=(sum(a for a,b in xs)/len(xs),sum(b for a,b in xs)/len(xs))
    deaths=collections.defaultdict(list)
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e.get('by') is not None: deaths[e['v']].append(e['r'])
    out=[]
    for cid,b in br.items():
        if cid not in ch: continue
        rs=sorted(r for r,x in b.items() if x=='R')
        runs=[]
        for r in rs:
            if runs and r-runs[-1][1]<=2: runs[-1][1]=r
            else: runs.append([r,r])
        c=ch[cid]; t=team[cid]
        for s,e_ in runs:
            i=ri.get(s)
            if i is None or c['x'][i] is None: continue
            x,y=c['x'][i],c['y'][i]
            died=any(s<=dr<=e_+3 for dr in deaths[cid])
            hp=c['hp'][i]/max(1,c['maxHp'][i] or 1)
            dsp=max(abs(x-cen[t][0]),abs(y-cen[t][1]))
            na=99; ne=0
            for o in R['champions']:
                if o['id']==cid or not o['alive'][i] or o['x'][i] is None: continue
                dd=max(abs(o['x'][i]-x),abs(o['y'][i]-y))
                if o['team']==t: na=min(na,dd)
                elif dd<=6: ne+=1
            out.append((died,hp,dsp,na,ne,e_-s+1))
    return out
if __name__=='__main__':
    ps=glob.glob(B+'/*.repl26a')
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ps,chunksize=8) for x in o]
    n=len(S); print('retreat runs',n,'died %.1f%%'%(100*sum(s[0] for s in S)/n))
    def tab(lab,f,bins):
        print(lab)
        for lo,hi in bins:
            xs=[s for s in S if lo<=f(s)<hi]
            if xs: print('  [%s,%s) n=%6d died %.1f%%  len %.1f'%(lo,hi,len(xs),100*sum(s[0] for s in xs)/len(xs),sum(s[5] for s in xs)/len(xs)))
    tab('by spawn distance',lambda s:s[2],[(0,8),(8,14),(14,20),(20,30),(30,99)])
    tab('by nearest ally',lambda s:s[3],[(0,4),(4,7),(7,11),(11,16),(16,100)])
    tab('by enemies within 6',lambda s:s[4],[(0,1),(1,2),(2,3),(3,9)])
    tab('by hp',lambda s:s[1],[(0,.3),(.3,.6),(.6,.9),(.9,1.01)])
    print('ally nearer than spawn (and ally within 10):')
    for k in (True,False):
        xs=[s for s in S if (s[3]<s[2] and s[3]<=10)==k and s[2]>=10]
        print('  %s n=%d died %.1f%%'%(k,len(xs),100*sum(s[0] for s in xs)/max(1,len(xs))))
