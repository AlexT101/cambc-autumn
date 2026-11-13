import json,gzip,glob,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; WHO=sys.argv[2] if len(sys.argv)>2 else None
en=json.load(open(ROOT+'/enums.json'))['champions']
idx={g['dir']:g['teams'] for g in json.load(open(ROOT+'/index.json'))['games']}
def one(d):
    meta=json.load(open(d+'/meta.json')); tn=idx.get(os.path.basename(d))
    mp=json.load(open(os.path.normpath(os.path.join(d,meta['mapFile']))))
    tiles={g['id']:set(map(tuple,g['tiles'])) for g in mp['groups']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rid={r:i for i,r in enumerate(R['round'])}
    C={c['id']:c for c in R['champions']}
    typ={c['id']:en[c['type']] for c in meta['champions']}
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='capture': continue
        sh=e['shares']
        if len(sh)!=1: continue
        a=sh[0][0]
        if typ.get(a)!='Prism' or sh[0][1]<=0: continue
        team=C[a]['team']
        if WHO and tn and tn[team]!=WHO: continue
        P=e['r']; T=tiles.get(e['g'],set())
        i=rid.get(P-1)
        if i is None: continue
        stood=0
        for k in range(i,max(-1,i-12),-1):
            c=C[a]
            if c['x'][k] is not None and (c['x'][k],c['y'][k]) in T: stood+=1
            else: break
        ally_pre=False
        for k in range(max(0,i-6),i+1):
            for b,c in C.items():
                if b!=a and c['team']==team and c['x'][k] is not None and (c['x'][k],c['y'][k]) in T: ally_pre=True
        out.append((stood,ally_pre,sh[0][1]))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    S=[]
    with ProcessPoolExecutor(32) as ex:
        for s in ex.map(one,ds,chunksize=4): S+=s
    n=len(S); print(WHO,'sole Prism captures',n,'per game',n/len(ds))
    print('mean rounds Prism stood before payout',statistics.mean(x[0] for x in S),'ally on tiles in last 6',sum(x[1] for x in S)/n)
    print('stood dist',collections.Counter(min(x[0],8) for x in S).most_common())
    print('gems per capture',statistics.mean(x[2] for x in S))
