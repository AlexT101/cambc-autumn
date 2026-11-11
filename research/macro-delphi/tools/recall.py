import json,gzip,glob,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    ri={r:i for i,r in enumerate(R['round'])}
    C={c['id']:c for c in R['champions']}
    out=collections.Counter(); after=collections.Counter()
    evs=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    nxt=collections.defaultdict(list)
    for e in evs:
        if e['k'] in ('shop','tribute_start','death','recall_start') and 'a' in e: nxt[e['a']].append((e['r'],e['k']))
    for e in evs:
        if e['k']!='recall_end': continue
        a=e['a']; r=e['r']; i=ri.get(r-6)
        if i is None: continue
        c=C[a]; hpf=c['hp'][i]/max(1,c['maxHp'][i])
        k='P' if names[a]=='Prism' else 'o'
        hb='hp<0.5' if hpf<0.5 else 'hp<0.9' if hpf<0.9 else 'hp>=0.9'
        gb='gems0' if e['gems']==0 else 'gems>0'
        out[k,hb,gb]+=1
        # what happens within 3 rounds after arrival
        acts=set(kk for rr,kk in nxt[a] if r<=rr<=r+3)
        after[k,'shop' in acts]+=1
        out[k,'n']+=1
    return out,after
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.Counter(); ag2=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o,a in ex.map(one,dirs): agg.update(o); ag2.update(a)
    n=len(dirs)
    for k,v in sorted(agg.items()): print(k, round(v/n,2),'per game')
    print(ag2)
if __name__=='__main__': main()
