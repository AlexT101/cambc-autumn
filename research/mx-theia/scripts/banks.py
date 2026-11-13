# Tribute starts by champion type: count per game, mean bag, completion rate; recall starts per type and hp fraction.
import json,gzip,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx=json.load(open(ROOT+'/index.json'))
dirs=sorted(set(g['dir'] for g in idx['games']))
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json'))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
        R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    typ={c['id']:en[c['type']] for c in meta['champions']}
    CH={c['id']:c for c in R['champions']}
    out=collections.defaultdict(list)
    for e in ev:
        if e['k']=='tribute_start' and e['r']<=600:
            out[('ts',typ[e['a']])].append(e['gems'])
        elif e['k']=='tribute_end' and e['r']<=600:
            out[('te',typ[e['a']])].append(e['gems'])
        elif e['k']=='recall_start' and e['r']<=600:
            c=CH[e['a']]; i=max(0,e['r']-2)
            hp=c['hp'][i]/max(1,c['maxHp'][i]) if c['hp'][i] is not None else 1
            out[('rc',typ[e['a']])].append(hp)
        elif e['k']=='recall_end' and e['r']<=600:
            out[('re',typ[e['a']])].append(1)
    ntype=collections.Counter(typ.values())
    return out,ntype
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,dirs,chunksize=4) if r]
    A=collections.defaultdict(list); N=collections.Counter()
    for o,n in res:
        for k,v in o.items(): A[k]+=v
        N.update(n)
    for t in sorted(N):
        ts=A[('ts',t)]; te=A[('te',t)]; rc=A[('rc',t)]; re_=A[('re',t)]
        if not N[t]: continue
        print(f"{t:14s} n={N[t]:5d} tribStarts/body {len(ts)/N[t]:.1f} meanBag {statistics.mean(ts) if ts else 0:.0f} done/body {len(te)/N[t]:.1f} doneBag {statistics.mean(te) if te else 0:.0f} | recallStart/body {len(rc)/N[t]:.1f} done {len(re_)/N[t]:.1f} hp>=.9 {sum(h>=.9 for h in rc)/max(1,len(rc)):.2f} hp<.5 {sum(h<.5 for h in rc)/max(1,len(rc)):.2f}")
