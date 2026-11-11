import json,gzip,glob,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def cheb(a,b):
    if None in a or None in b: return 99
    return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    C={c['id']:c for c in R['champions']}
    out=collections.Counter()
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('by') is None or names.get(e['by'])!='Prism': continue
        v=e['v']; k=e['by']; r=e['r']
        cls='pair' if names[v] in ('Cassi','Issac') else names[v] if names[v]=='Prism' else 'other'
        for lag in (1,2,3,5):
            i=ri.get(r-lag)
            if i is None: continue
            vs = k in C[v]['sees'][i]
            ts = any(k in C[a]['sees'][i] for a in C if team[a]==team[v] and C[a]['alive'][i])
            dd = cheb((C[v]['x'][i],C[v]['y'][i]),(C[k]['x'][i],C[k]['y'][i]))
            out[cls,lag,'victim_sees']+=vs; out[cls,lag,'team_sees']+=ts; out[cls,lag,'n']+=1
            out[cls,lag,'d<=5']+= dd<=5; out[cls,lag,'d<=8']+=dd<=8
            # focus ratio
            fo=C[k]['foc'][i]; hp=C[v]['hp'][i]
            out[cls,lag,'burst>=hp']+= (2.5*fo>=hp)
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.Counter()
    for o in ProcessPoolExecutor(32).map(one,dirs): agg.update(o)
    for cls in ('pair','Prism','other'):
        for lag in (1,2,3,5):
            n=agg[cls,lag,'n']
            if n: print(cls,lag,n,{k: round(agg[cls,lag,k]/n,2) for k in ('victim_sees','team_sees','d<=5','d<=8','burst>=hp')})
if __name__=='__main__': main()
