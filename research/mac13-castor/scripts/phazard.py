import json,gzip,glob,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    meta=json.load(open(d+'/meta.json'))
    pr={c['id']:c['team'] for c in meta['champions'] if en[c['type']]=='Prism'}
    if len(pr)!=2: return None
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; C={c['id']:c for c in R['champions']}
    deaths={}
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e['v'] in pr and e['v'] not in deaths: deaths[e['v']]=e['r']
    first=min(deaths.values()) if deaths else 10**9
    H=collections.Counter(); D=collections.Counter()
    for v,team in pr.items():
        P=C[v]
        for i,r in enumerate(rounds):
            if r>=first: break
            if not P['alive'][i] or P['x'][i] is None: continue
            p=(P['x'][i],P['y'][i])
            a=e=0
            for c in R['champions']:
                if c['id']==v or not c['alive'][i] or c['x'][i] is None: continue
                if cheb((c['x'][i],c['y'][i]),p)<=8:
                    if c['team']==team: a+=1
                    else: e+=1
            if e==0: continue
            key=(min(a,3),min(e,3))
            H[key]+=1
            if deaths.get(v,10**9)<=r+5 and deaths.get(v)==first: D[key]+=1
    return H,D
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    H=collections.Counter(); D=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for s in ex.map(one,ds,chunksize=4):
            if s: H.update(s[0]); D.update(s[1])
    print('allies enemies rounds first-death-within-5 per-1000-rounds')
    for k in sorted(H): print(k[0],k[1],H[k],D[k],'%.1f'%(1000*D[k]/H[k]))
