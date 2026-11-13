# The Prism's capture cycle (r<=LIMIT): rounds from its previous payout (or death/respawn) to its next payout, split
# into rounds walking (moved, no camp damage), clearing (dealt camp damage), holding (on a capture hold), other.
# By whether allies dealt most of the group's clear. W vs L.
import json,gzip,sys,os,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; LIMIT=int(sys.argv[2]) if len(sys.argv)>2 else 600
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]; R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    w=meta['result']['winner']; P={team[i]:i for i,n in names.items() if n=='Prism'}
    rd={r:i for i,r in enumerate(R['round'])}; CH={c['id']:c for c in R['champions']}
    hit=collections.defaultdict(set)  # pid -> rounds with camp damage
    dmg=collections.defaultdict(collections.Counter); g_of={}
    out=collections.Counter()
    last={pid:1 for pid in P.values()}
    for e in ev:
        if e['r']>LIMIT: break
        if e['k'] in ('attack','cast') and e.get('cdmg'):
            if e['a'] in last: hit[e['a']].add(e['r'])
            for camp,amt in e['cdmg']: dmg[camp][team.get(e['a'],-1)]+=amt; 
        if e['k']=='camp_death': g_of[e['camp']]=e['g']
        if e['k']=='death' and e['v'] in last: last[e['v']]=None
        if e['k']=='capture' and e['team'] in (0,1):
            camps=[c for c,g in g_of.items() if g==e['g']]
            for pid in last:
                if team[pid]!=e['team'] or not any(s[0]==pid for s in e['shares']): continue
                tot=collections.Counter(); [tot.update(dmg.get(c,{})) for c in camps]
                # ally share of our clear damage: not separable by team only; use Prism's own hits instead
                c=CH[pid]; a=last[pid]
                if a is None:
                    # from respawn: first alive round after death
                    i=rd.get(e['r']); j=i
                    while j>0 and c['alive'][j-1]: j-=1
                    a=R['round'][j]
                lab='W' if team[pid]==w else 'L'
                walk=clear=other=0
                for r in range(a+1,e['r']-5):
                    t=rd.get(r)
                    if t is None or not c['alive'][t]: other+=1; continue
                    if r in hit[pid]: clear+=1
                    elif (c['x'][t],c['y'][t])!=(c['x'][t-1],c['y'][t-1]): walk+=1
                    else: other+=1
                out[(lab,'n')]+=1; out[(lab,'walk')]+=walk; out[(lab,'clear')]+=clear; out[(lab,'other')]+=other; out[(lab,'gems')]+=sum(s[1] for s in e['shares'] if s[0]==pid)
                last[pid]=e['r']
            for cc in camps: g_of.pop(cc,None); dmg.pop(cc,None)
    return out
def main():
    idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
    with ProcessPoolExecutor(32) as ex: res=[x for x in ex.map(one,dirs,chunksize=8) if x]
    T=collections.Counter()
    for r in res: T.update(r)
    for lab in 'WL':
        n=T[(lab,'n')]
        print(lab,'Prism captures %d; per capture: gems %.1f, walk %.1f, clear %.1f, other %.1f, hold 6'%(n,T[(lab,'gems')]/n,T[(lab,'walk')]/n,T[(lab,'clear')]/n,T[(lab,'other')]/n))
if __name__=='__main__': main()
