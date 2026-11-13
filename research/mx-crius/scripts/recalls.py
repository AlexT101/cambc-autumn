"""Completed recalls: per type, HP fraction at start, gold at arrival, shop on arrival, distance from spawn at start,
rounds until next camp hit after arrival; walks home on foot (arrive on spawn without recall) likewise."""
import json, gzip, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
CH=json.load(open(ROOT+'/enums.json'))['champions']
def one(d):
    meta=json.load(open(d+'/meta.json')); typ={c['id']:CH[c['type']] for c in meta['champions']}
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; ri={r:i for i,r in enumerate(rounds)}
    ci={c['id']:c for c in R['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    start={}; out=[]; shops=collections.defaultdict(list); camphit=collections.defaultdict(list)
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    for e in ev:
        if e['k']=='shop': shops[e['a']].append(e['r'])
        if e['k'] in ('attack','cast') and e.get('cdmg'): camphit[e['a']].append(e['r'])
    for e in ev:
        if e['k']=='recall_start': start[e['a']]=e
        elif e['k']=='recall_end':
            s=start.pop(e['a'],None)
            if not s: continue
            a=e['a']; c=ci[a]; i=ri.get(s['r']-1)
            if i is None: continue
            hpf=c['hp'][i]/max(1,c['maxHp'][i]); sp=mp['spawn'][team[a]]
            x,y=c['x'][i],c['y'][i]
            dsp=max(0,x-sp['maxX'],sp['minX']-x,y-sp['maxY'],sp['minY']-y) if x is not None else None
            shop=any(e['r']<=r<=e['r']+1 for r in shops[a])
            nxt=[r for r in camphit[a] if r>e['r']]
            out.append((typ[a],hpf,shop,dsp,(nxt[0]-e['r']) if nxt else None,c['gold'][i]))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    N=len(ds)
    tab=collections.defaultdict(list)
    for s in S: tab[s[0]].append(s)
    print('%-13s %8s %6s %6s %6s %6s %6s %6s'%('type','rec/game','hp<.5','hp>.9','shop','dist','next','gold'))
    for t,xs in sorted(tab.items(),key=lambda kv:-len(kv[1])):
        nx=[x[4] for x in xs if x[4] is not None]; ds_=[x[3] for x in xs if x[3] is not None]
        print('%-13s %8.2f %6.2f %6.2f %6.2f %6.1f %6.1f %6.0f'%(t,len(xs)/N,sum(1 for x in xs if x[1]<.5)/len(xs),sum(1 for x in xs if x[1]>.9)/len(xs),sum(1 for x in xs if x[2])/len(xs),st.mean(ds_),st.median(nx) if nx else 0,st.mean(x[5] for x in xs)))
