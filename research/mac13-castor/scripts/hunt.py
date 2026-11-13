import json,gzip,glob,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    meta=json.load(open(d+'/meta.json'))
    pr=[c['id'] for c in meta['champions'] if en[c['type']]=='Prism']
    if len(pr)!=2: return collections.Counter()
    R=json.load(gzip.open(d+'/rounds.json.gz')); C={c['id']:c for c in R['champions']}
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    deaths=[(e['r'],e['v'],e.get('by')) for e in ev if e['k']=='death' and e['v'] in pr]
    out=collections.Counter(); last=-99
    for i,r in enumerate(R['round']):
        if r-last<15: continue
        for a,b in ((pr[0],pr[1]),(pr[1],pr[0])):
            A,B=C[a],C[b]
            if not(A['alive'][i] and B['alive'][i]) or A['x'][i] is None or B['x'][i] is None: continue
            ratio=A['foc'][i]/max(1,B['foc'][i]); d=cheb((A['x'][i],A['y'][i]),(B['x'][i],B['y'][i]))
            if ratio<1.25 or not(6<=d<=8) or b not in A['sees'][i] or A['hp'][i]<0.7*A['maxHp'][i]: continue
            out['opp']+=1; last=r
            k=[x for x in deaths if r<x[0]<=r+15]
            if k and k[0][1]==b: out['strong_kills']+=1
            if k and k[0][1]==a: out['strong_dies']+=1
            out['bag_b']+=B['gems'][i] or 0
            # did A move closer within next 3 rounds
            j=min(i+3,len(R['round'])-1)
            if A['x'][j] is not None and B['x'][j] is not None and cheb((A['x'][j],A['y'][j]),(B['x'][j],B['y'][j]))<=5: out['closed_in_3']+=1
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one,ds,chunksize=4): tot+=o
    print(dict(tot), 'games',len(ds), 'mean weak bag', tot['bag_b']/max(1,tot['opp']))
