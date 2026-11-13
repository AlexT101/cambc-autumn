"""Median Strength, Focus, max health and gold earned by champion type at rounds T. usage: py stats.py EXTRACT"""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; TS=[150,300,500,800]
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); typ={c['id']:CH[c['type']] for c in m['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    out=collections.defaultdict(list)
    for c in R['champions']:
        for T in TS:
            i=ri.get(T)
            if i is None: continue
            out[(typ[c['id']],T)].append((c['str'][i],c['foc'][i],c['maxHp'][i],c['earned'][i],c['gems'][i] or 0))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    tot=collections.defaultdict(list)
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one,ds,chunksize=8):
            for k,v in o.items(): tot[k]+=v
    for ty in ('Prism','Vesper Vale','Ryth','Vendetta','Cassi','Issac','Marcella','Heart of Ruin','Willow'):
        print(ty)
        for T in TS:
            X=tot.get((ty,T))
            if not X: continue
            med=lambda j: sorted(x[j] or 0 for x in X)[len(X)//2]
            print('  r%-4d n=%5d str %6.0f foc %6.0f maxhp %6.0f gold earned %6.0f bag %4.0f'%(T,len(X),med(0),med(1),med(2),med(3),med(4)))
