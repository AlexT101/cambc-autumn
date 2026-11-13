"""Champion kills: did the victim see the killer at its turn start, 1 and 3 rounds before death? Did the killer see the victim?"""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]; CH=json.load(open(R+'/enums.json'))['champions']
def one(p):
    d=os.path.dirname(p); m=json.load(open(p)); typ={c['id']:CH[c['type']] for c in m['champions']}
    RR=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(RR['round'])}; ci={c['id']:c for c in RR['champions']}
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('by') is None or e.get('linked'): continue
        v,k=e['v'],e['by']; row=[]
        for lag in (0,1,3,6):
            i=ri.get(e['r']-lag)
            if i is None: row.append(None); continue
            vs=ci[v].get('sees',[None]*len(RR['round']))[i] or []
            ks=ci[k].get('sees',[None]*len(RR['round']))[i] or []
            row.append((k in vs, v in ks))
        out.append((typ[v],row))
    return out
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json')
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ps,chunksize=8) for x in o]
    for j,lag in enumerate((0,1,3,6)):
        xs=[s[1][j] for s in S if s[1][j] is not None]
        print('lag %d: victim saw killer %.2f, killer saw victim %.2f, killer saw & victim not %.2f'%(lag,sum(a for a,b in xs)/len(xs),sum(b for a,b in xs)/len(xs),sum(1 for a,b in xs if b and not a)/len(xs)))
