import json,gzip,glob,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def cheb(a,b):
    if None in a or None in b: return 99
    return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    out=collections.Counter()
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('by') is None or team.get(e['by'])==team[e['v']]: continue
        k=e['by']; t=team[k]; i=ri.get(e['r'])
        if i is None: continue
        out['kills']+=1; out['bag']+=e['gems']
        if names[k]=='Prism': continue
        out['ally_kills']+=1; out['ally_bag']+=e['gems']
        P=[p for p in C if team[p]==t and names[p]=='Prism' and C[p]['alive'][i]]
        if P and e['gems']>0 and cheb((C[P[0]]['x'][i],C[P[0]]['y'][i]),tuple(e['at']))<=4:
            out['prism_in_reach']+=1; out['reach_bag']+=e['gems']
    return out
def main():
    agg=collections.Counter(); n=0
    for o in ProcessPoolExecutor(32).map(one,[x[:-10] for x in glob.glob(A+'/*/meta.json')]): agg.update(o); n+=1
    print({k:round(v/n,2) for k,v in agg.items()})
if __name__=='__main__': main()
