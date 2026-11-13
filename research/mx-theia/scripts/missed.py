# Missed duel openings: rounds where a Prism sees the enemy Prism within ability range (4) with its stun slot (0)
# ready, no Prism-to-Prism unit cast between them in the 30 rounds before, and does not cast at it. Split by Focus ratio;
# for the episodes (first such round), who died within 30 rounds.
import json,gzip,sys,os,collections
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]; R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; P=[i for i,n in names.items() if n=='Prism']
    if len(P)!=2: return None
    CH={c['id']:c for c in R['champions']}
    casts=collections.defaultdict(set)
    for e in ev:
        if e['k']=='cast' and e['a'] in P and e.get('tgt') in P: casts[e['a']].add(e['r'])
    deaths=[(e['r'],e['v']) for e in ev if e['k']=='death' and e['v'] in P]
    allc=set().union(*casts.values()) if casts else set()
    out=collections.Counter(); last={}
    for t,r in enumerate(R['round']):
        for a in P:
            b=[x for x in P if x!=a][0]; A,B=CH[a],CH[b]
            if not (A['alive'][t] and B['alive'][t]): continue
            if b not in (A['sees'][t] or []): continue
            if cheb((A['x'][t],A['y'][t]),(B['x'][t],B['y'][t]))>4: continue
            if A['cd0'][t]!=0: continue
            if any(r-30<=x<r for x in allc): continue
            ratio=A['foc'][t]/max(1,B['foc'][t]); k='<0.8' if ratio<0.8 else '0.8-1.25' if ratio<=1.25 else '>1.25'
            cast=r in casts[a]
            out[(k,'cast' if cast else 'held')]+=1
            if not cast and r-last.get(a,-99)>30:
                last[a]=r; out[(k,'ep')]+=1
                out[(k,'ep_a_died')]+=any(r<=x<=r+30 and v==a for x,v in deaths); out[(k,'ep_b_died')]+=any(r<=x<=r+30 and v==b for x,v in deaths)
                if r<400: out[(k,'ep_early')]+=1
    return out
if __name__=='__main__':
    idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
    with ProcessPoolExecutor(32) as ex: res=[x for x in ex.map(one,dirs,chunksize=8) if x]
    T=collections.Counter()
    for r in res: T.update(r)
    n=len(res); print('games',n)
    for k in ('<0.8','0.8-1.25','>1.25'):
        print('%-9s rounds: cast %d held %d; held episodes %d (%.2f/game, before r400 %d): holder died %.2f, enemy died %.2f'%(k,T[(k,'cast')],T[(k,'held')],T[(k,'ep')],T[(k,'ep')]/n,T[(k,'ep_early')],T[(k,'ep_a_died')]/max(1,T[(k,'ep')]),T[(k,'ep_b_died')]/max(1,T[(k,'ep')])))
