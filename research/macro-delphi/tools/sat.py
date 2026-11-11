import json,gzip,glob,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json')); w=M['result']['winner']
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    out=collections.Counter()
    P={team[c]:c for c in C if names[c]=='Prism'}
    for t,p in P.items():
        sat_rounds=0; surplus=[]
        for i,r in enumerate(R['round']):
            if not C[p]['alive'][i]: continue
            mh=max([C[e]['maxHp'][i] for e in C if team[e]!=t] or [1])
            fsat=mh/2.5
            F=C[p]['foc'][i]; g=C[p]['gems'][i]
            if F>fsat:
                sat_rounds+=1
                surplus.append(min(g,(F-fsat)/1.5))
        out['prisms']+=1
        out['sat_rounds']+=sat_rounds
        if surplus: out['surplus_mean_x']+=st.mean(surplus); out['with_sat']+=1
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and names[e['v']]=='Prism':
            i=ri.get(e['r']-1)
            if i is None: continue
            v=e['v']; t=team[v]
            mh=max(C[x]['maxHp'][i] for x in C if team[x]!=t)
            if C[v]['foc'][i]>mh/2.5:
                out['sat_deaths']+=1; out['sat_death_gems']+=e['gems']; out['sat_death_lost']+= (w!=t)
    return out
def main():
    agg=collections.Counter(); n=0
    for o in ProcessPoolExecutor(32).map(one,[x[:-10] for x in glob.glob(A+'/*/meta.json')]): agg.update(o); n+=1
    print(n, dict(agg))
    print('sat rounds per prism %.0f; prisms ever saturated %d/%d; mean surplus gems while saturated %.0f'%(agg['sat_rounds']/agg['prisms'],agg['with_sat'],agg['prisms'],agg['surplus_mean_x']/max(1,agg['with_sat'])))
if __name__=='__main__': main()
