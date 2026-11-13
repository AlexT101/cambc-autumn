# Captures by non-Prism allies while their Prism lives: Chebyshev distance from the Prism at payout; Prism share.
import json,gzip,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; CAND=sys.argv[2] if len(sys.argv)>2 else None
en=json.load(open(ROOT+'/enums.json'))['champions']
idx=json.load(open(ROOT+'/index.json'))
rows={}
for g in idx['games']: rows.setdefault(g['dir'],g)
def one(item):
    dname,row=item; d=os.path.join(ROOT,dname)
    try:
        meta=json.load(open(d+'/meta.json')); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]; R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    win=meta['result']['winner']
    typ={c['id']:en[c['type']] for c in meta['champions']}; team_of={c['id']:c['team'] for c in meta['champions']}
    CH={c['id']:c for c in R['champions']}
    prism={t:[c for c in CH if typ[c]=='Prism' and team_of[c]==t] for t in (0,1)}
    groups={g['id']:g for g in mp['groups']}
    out=collections.Counter()
    def key(t): return (row['teams'][t]==CAND) if CAND else (t==win)
    for e in ev:
        if e['k']!='capture' or e['team'] not in (0,1) or e['r']>600: continue
        t=e['team']
        if not prism[t]: continue
        p=CH[prism[t][0]]; i=max(0,e['r']-1)
        gems=sum(s[1] for s in e['shares'])
        pg=sum(s[1] for s in e['shares'] if s[0]==prism[t][0])
        out[(key(t),'gems')]+=gems; out[(key(t),'prism_gems')]+=pg
        if pg>0 or not p['alive'][i] or p['x'][i] is None: continue
        G=groups.get(e['g'])
        if not G or 'Monolith' in G['types'] or G['gems']==0: continue
        tiles=G['tiles']
        dd=min(max(abs(p['x'][i]-x),abs(p['y'][i]-y)) for x,y in tiles)
        b='<=6' if dd<=6 else '7-12' if dd<=12 else '13-24' if dd<=24 else '25+'
        out[(key(t),'ally_cap_'+b)]+=gems
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,list(rows.items()),chunksize=4) if r]
    T=collections.Counter()
    for r in res: T.update(r)
    n=len(res)
    for s in (True,False):
        lab=('CAND' if s else 'REF') if CAND else ('W' if s else 'L')
        print(lab,'prism share of capture gems r<=600: %.3f'%(T[(s,'prism_gems')]/max(1,T[(s,'gems')])), {k[1]:round(v/n,1) for k,v in sorted(T.items()) if k[0]==s and k[1].startswith('ally')})
