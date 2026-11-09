"""Contact rate: champion-rounds with an enemy champion within 4 (cast range), and champion-hitting casts per contact round."""
import beh, cmb_run, sys, os, collections
from multiprocessing import Pool
def cr(j):
    k,d,T=j
    try: meta,rd,ev=beh.load(d)
    except Exception: return (k,None)
    team={c['id']:c['team'] for c in meta['champions']}
    C=rd['champions']; n=len(rd['round']); acc=collections.Counter()
    for c in C:
        s='us' if c['team']==T else 'op'
        foes=[o for o in C if o['team']!=c['team']]
        for i in range(n):
            if not c['alive'][i]: continue
            acc['alive_'+s]+=1
            x,y=c['x'][i],c['y'][i]
            if any(o['alive'][i] and max(abs(o['x'][i]-x),abs(o['y'][i]-y))<=4 for o in foes): acc['contact_'+s]+=1
    for e in ev:
        if e['k']=='cast' and e.get('dmg'):
            s='us' if team[e['a']]==T else 'op'
            acc['ccast_'+s]+=1; acc['ccastdmg_'+s]+=sum(x[1] for x in e['dmg'] if team.get(x[0])!=team[e['a']])
    return (k,acc)
if __name__=='__main__':
    jobs=cmb_run.live(['v87-r2','v89-r2'])
    for a in sys.argv[1:]: jobs+=cmb_run.loc(a,'loc:'+os.path.basename(a))
    with Pool(24) as p: res=p.map(cr,jobs,chunksize=8)
    G=collections.defaultdict(collections.Counter); N=collections.Counter()
    for k,a in res:
        if a: G[k].update(a); N[k]+=1
    for k in sorted(G):
        a=G[k]
        for s in ('us','op'):
            print(f"{k:22} {s} contact share {a['contact_'+s]/a['alive_'+s]:.3f}  contact rds/game {a['contact_'+s]/N[k]:.0f}  champ casts per 100 contact rds {100*a['ccast_'+s]/a['contact_'+s]:.2f}  dmg/cast {a['ccastdmg_'+s]/max(1,a['ccast_'+s]):.0f}")
