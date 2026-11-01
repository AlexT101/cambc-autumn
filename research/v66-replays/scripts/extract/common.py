import json, gzip, os, sys
from collections import Counter, defaultdict
S=os.environ.get('V66_SCRATCH', 'replays/v66-analysis')
EX=os.environ.get('V66_EXTRACT', S+'/ex')
US='newer team'
def short(n):
    return {'Intercontinental Fish':'Fish','Mite':'Mite','Univardisty of Shingtonwash':'UoS','prism best girl':'PBG'}.get(n,n)
def games(distinct=True):
    ix=json.load(open(EX+'/index.json'))['games']
    seen=set(); out=[]
    for r in ix:
        if distinct and r['dir'] in seen: continue
        seen.add(r['dir'])
        us=r['teams'].index(US)
        r=dict(r); r['us']=us; r['opp']=short(r['teams'][1-us]); r['won']=r['winner']==us
        r['kindg']=json.load(open(os.path.join(os.path.dirname(r['source']),'group.json')))['group']['kind'] if os.path.exists(os.path.join('.',os.path.dirname(r['source']),'group.json')) else None
        out.append(r)
    return out
def meta(d): return json.load(open(f'{EX}/{d}/meta.json'))
def mapj(m): return json.load(open(f"{EX}/maps/{m['map']['hash']}.json"))
def events(d): return [json.loads(l) for l in gzip.open(f'{EX}/{d}/events.jsonl.gz','rt')]
def rounds(d): return json.load(gzip.open(f'{EX}/{d}/rounds.json.gz'))
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def spawn_field(mp,t):
    from collections import deque
    W,H=mp['width'],mp['height']
    blk=set(map(tuple,mp['walls']))|set(map(tuple,mp['holes']))|set(map(tuple,mp['altars']))
    s=mp['spawn'][t]; D={}; q=deque()
    for x in range(s['minX'],s['maxX']+1):
        for y in range(s['minY'],s['maxY']+1): D[(x,y)]=0; q.append((x,y))
    while q:
        p=q.popleft()
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                n=(p[0]+dx,p[1]+dy)
                if 0<=n[0]<W and 0<=n[1]<H and n not in blk and n not in D: D[n]=D[p]+1; q.append(n)
    return D
