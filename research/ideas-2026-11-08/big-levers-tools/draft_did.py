# Difference-in-differences of scrim win rate (vs Fish+Mite) on maps whose own comp changed between eras vs unchanged.
import json,collections,numpy as np
G=[json.loads(l) for l in open('research/ladder-scrims-2026-11-06/data/games.jsonl')]
G=[g for g in G if g.get('status')=='finished' and g['opp_name'] in ('Intercontinental Fish','Mite')]
def era_stats(vs):
    d=collections.defaultdict(list); comp={}
    for g in G:
        if g['version'] in vs:
            d[g['map']].append(g['result']=='win'); comp.setdefault(g['map'],tuple(sorted(g['our_picks'])))
    return d,comp
def did(A,B,boot=2000):
    da,ca=era_stats(A); db,cb=era_stats(B)
    ms=[m for m in da if m in db]
    ch=[m for m in ms if ca[m]!=cb[m]]; un=[m for m in ms if ca[m]==cb[m]]
    def delta(lst): return np.mean([np.mean(db[m])-np.mean(da[m]) for m in lst])
    est=delta(ch)-delta(un)
    rng=np.random.default_rng(0); bs=[]
    for _ in range(boot):
        c=rng.choice(ch,len(ch)); u=rng.choice(un,len(un)); bs.append(delta(c)-delta(u))
    print(f'{A}->{B}: changed {len(ch)} maps d={delta(ch):+.3f}, unchanged {len(un)} d={delta(un):+.3f}; DiD {est:+.3f} CI {np.percentile(bs,2.5):+.3f}..{np.percentile(bs,97.5):+.3f}')
    return ch,ca,cb,da,db
did([78,80],[81,82]); ch,ca,cb,da,db=did([81,82],[83,84,85,86,87,88,89])
did([78,80],[83,84,85,86,87,88,89])
# what changed v82->v83 on changed maps: champion swaps
sw=collections.Counter()
for m in ch:
    for c in set(cb[m])-set(ca[m]): sw['+'+c]+=1
    for c in set(ca[m])-set(cb[m]): sw['-'+c]+=1
print(sw.most_common())
