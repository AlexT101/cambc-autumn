"""Shared helpers for the second-order analyses (run scripts from the repo root).
Extract side: per-game arrays (alive/pos/hp by round), deaths, spawn fields.
Trace side: a compact per-turn cache of our decisions (build with `python3 so.py cache`)."""
import sys, os, json, gzip, pickle
from collections import defaultdict, Counter
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE+'/../extract'); sys.path.insert(0, HERE+'/../trace')
import common as C
import tlib
CACHE=os.environ.get('SO_CACHE', 'replays/v66-analysis/so_cache')
NPROC=28

def manifest():
    M={}
    for g in json.load(open('replays/v66/manifest.json'))['games']:
        M[g['replay']]=g['group'][:8]+'-'+str(g['position'])
    return M

class Game:
    """One distinct extract game. Pick units: C&I count as one unit (both bodies share life)."""
    def __init__(s, g):
        s.g=g; s.dir=g['dir']; s.us=g['us']; s.opp=g['opp']; s.won=g['won']; s.mapname=g['map']
        s.meta=C.meta(s.dir); s.mp=C.mapj(s.meta); s.ev=C.events(s.dir); s.R=C.rounds(s.dir)
        s.team={c['id']:c['team'] for c in s.meta['champions']}
        s.name={c['id']:c['name'] for c in s.meta['champions']}
        s.ch={c['id']:c for c in s.R['champions']}
        s.rnd=s.R['round']; s.N=len(s.rnd)
        s.idx={r:i for i,r in enumerate(s.rnd)}
        # pick units: Issac folds into Cassi
        s.unit={}
        for c in s.meta['champions']:
            s.unit[c['id']]=c['id']
        for c in s.meta['champions']:
            if c['name']=='Issac':
                cas=[d['id'] for d in s.meta['champions'] if d['team']==c['team'] and d['name']=='Cassi']
                if cas: s.unit[c['id']]=cas[0]
        s.units={t:sorted({s.unit[c] for c in s.team if s.team[c]==t}) for t in (0,1)}
        s.deaths=[e for e in s.ev if e['k']=='death' and e.get('linked') is None]
        s._sf=None
    def sf(s,t):
        if s._sf is None: s._sf=[C.spawn_field(s.mp,0),C.spawn_field(s.mp,1)]
        return s._sf[t]
    def pos(s,c,i):
        a=s.ch[c]
        if not a['alive'][i] or a['x'][i] is None: return None
        return (a['x'][i],a['y'][i])
    def alive_units(s,t,i):
        return sum(1 for u in s.units[t] if s.ch[u]['alive'][i])
    def own(s,t,p):
        """position in team A's frame"""
        if t==0 or p is None: return p
        W,H=s.mp['width'],s.mp['height']; sym=s.mp['symmetry']; x,y=p
        if sym=='horizontal': return (W-1-x,y)
        if sym=='vertical': return (x,H-1-y)
        return (W-1-x,H-1-y)
    def on_spawn(s,t,p):
        if p is None: return False
        sp=s.mp['spawn'][t]; return sp['minX']<=p[0]<=sp['maxX'] and sp['minY']<=p[1]<=sp['maxY']

def games():
    return C.games()

def pmap(fn, items, n=NPROC):
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(n) as ex: return list(ex.map(fn, items, chunksize=2))

# ---------------- trace cache ----------------
TT_KEYS=('a','p','q','hp','hq','mh','g','gq','d','dmg','fg','cl','cr','ch','chq','ls','fs','fe','ts')
def _cache_one(key):
    out=f'{CACHE}/{key}.pkl'
    if os.path.exists(out): return key
    v=json.load(open(f'{tlib.ROOT}/{key}/trace_validation.json')); trust=v.get('ladder_trusted_through') or 0
    turns={}  # (r,c)-> dict
    def get(r,c):
        k=(r,c)
        if k not in turns: turns[k]={'te':[], 'ta':[]}
        return turns[k]
    with gzip.open(f'{tlib.ROOT}/{key}/trace.stdout.gz','rt',errors='replace') as f:
        for l in f:
            tag=l[:2]
            if tag not in ('TT','TE','TA'): continue
            d=tlib.parse_line(l)
            try: r=int(d['r']); c=int(d['c'])
            except Exception: continue
            if r>trust: continue
            T=get(r,c)
            if tag=='TT':
                T['tt']={k:d[k] for k in TT_KEYS if k in d}; T['tt']['t']=d.get('t')
            elif tag=='TE':
                k=d.get('k')
                if k in ('comms_rx','rank','comms_tx','support','sides','farm_cand','cast_cand'): continue
                if k=='farm':
                    d={x:d[x] for x in ('k','best','v','m','steps','why','g','top','risky','shared') if x in d}
                    if 'top' in d: d['top']=d['top'].split(';')[0]
                d.pop('tag',None); d.pop('r',None); d.pop('c',None)
                T['te'].append(d)
            else:
                if d.get('a') in ('recall','set_priority','cancel_channel','buy_item'): 
                    T['ta'].append((d.get('a'),d.get('s'),d.get('rc'),d.get('ok'))); continue
                T['ta'].append((d.get('a'),d.get('s'),d.get('rc'),d.get('ok'),d.get('x')))
    pickle.dump({'trust':trust,'side':v.get('our_side'),'map':v.get('map'),'turns':turns},open(out,'wb'))
    return key
def build_cache():
    os.makedirs(CACHE,exist_ok=True)
    ks=[k for k,_ in tlib.keys()]
    pmap(_cache_one, ks)
    print(len(ks),'keys cached')
def tload(key):
    return pickle.load(open(f'{CACHE}/{key}.pkl','rb'))
def trace_keys():
    """(key, extract game dict) for traced keys; several keys can share one extract game (rematches)."""
    M=manifest(); G={g['source']:g for g in C.games(distinct=False)}
    ok={k for k,_ in tlib.keys()}
    out=[]
    for src,key in M.items():
        if key in ok and src in G: out.append((key,G[src]))
    return sorted(out,key=lambda x:x[0])

if __name__=='__main__' and sys.argv[1:]==['cache']:
    build_cache()
