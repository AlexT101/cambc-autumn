"""Cassi & Issac deaths by champions: which body died first (the kill victim), its health fraction 1 and 3 rounds
before, max health, killer type, round. usage: py cideath.py EXTRACT"""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); typ={c['id']:CH[c['type']] for c in m['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}; ch={c['id']:c for c in R['champions']}
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('by') is None or e.get('linked') or typ[e['v']] not in ('Cassi','Issac'): continue
        c=ch[e['v']]; h=[]
        for k in (1,3,6):
            i=ri.get(e['r']-k)
            h.append(c['hp'][i]/c['maxHp'][i] if i is not None and c['maxHp'][i] else None)
        i=ri.get(e['r']-1)
        out.append((typ[e['v']],typ.get(e['by'],'?'),h,c['maxHp'][i] if i is not None else None,e['r']))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    n=len(S); print('C&I kills',n,'per game %.2f'%(n/len(ds)),collections.Counter(s[0] for s in S).most_common())
    print('killers',collections.Counter(s[1] for s in S).most_common(5))
    for k,lab in ((0,'1 round before'),(1,'3 rounds before'),(2,'6 rounds before')):
        xs=[s[2][k] for s in S if s[2][k] is not None]; xs.sort()
        print('victim hp fraction %s: q %.2f %.2f %.2f; >=0.9: %.0f%%'%(lab,xs[len(xs)//4],xs[len(xs)//2],xs[3*len(xs)//4],100*sum(1 for x in xs if x>=.9)/len(xs)))
    P=[s for s in S if s[1]=='Prism']; xs=sorted(s[2][1] for s in P if s[2][1] is not None)
    print('by enemy Prism: victim hp 3 rounds before >=0.9: %.0f%%, median maxhp %d'%(100*sum(1 for x in xs if x>=.9)/len(xs),sorted(s[3] or 0 for s in P)[len(P)//2]))
