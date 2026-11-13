# Threat onsets for each Prism (an enemy comes within 8 after >=5 rounds with none): the nearest ally's distance then,
# and whether that Prism dies (first Prism death of the game) within the next 15 rounds. By bot.
import json,gzip,glob,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx={g['dir']:g['teams'] for g in json.load(open(ROOT+'/index.json'))['games']}
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def bucket(d): return '<=4' if d<=4 else '5-8' if d<=8 else '9-14' if d<=14 else '15-24' if d<=24 else '25+'
def one(d):
    meta=json.load(open(d+'/meta.json')); tn=idx.get(os.path.basename(d))
    pr={c['id']:c['team'] for c in meta['champions'] if en[c['type']]=='Prism'}
    if len(pr)!=2 or not tn: return None
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; C={c['id']:c for c in R['champions']}
    deaths={}
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e['v'] in pr and e['v'] not in deaths: deaths[e['v']]=e['r']
    first=min(deaths.values()) if deaths else 10**9
    out=[]
    for v,team in pr.items():
        P=C[v]; quiet=5; bot=tn[team] if isinstance(team,int) and team<len(tn) else str(team)
        for i,r in enumerate(rounds):
            if r>=first: break
            if not P['alive'][i] or P['x'][i] is None: quiet=0; continue
            p=(P['x'][i],P['y'][i]); en_near=0; na=99
            for c in R['champions']:
                if c['id']==v or not c['alive'][i] or c['x'][i] is None: continue
                dd=cheb((c['x'][i],c['y'][i]),p)
                if c['team']==team: na=min(na,dd)
                elif dd<=8: en_near+=1
            if en_near==0: quiet+=1; continue
            if quiet>=5:
                died=deaths.get(v)==first and first<=r+15
                out.append((bot,bucket(na),min(en_near,3),died))
            quiet=0
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    N=collections.Counter(); D=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for s in ex.map(one,ds,chunksize=4):
            for b,k,e,died in (s or []): N[(b,k)]+=1; D[(b,k)]+=died; N[('all',k,e)]+=1; D[('all',k,e)]+=died
    for k in sorted(N,key=str): print(k,N[k],D[k],'%.3f'%(D[k]/N[k]))
