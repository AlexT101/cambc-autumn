import hordash, json, collections, sys
from multiprocessing import Pool
D='/home/ubuntu/tmp-offload/handoff/gate/analysis/'
idx=json.load(open(D+'index.json'))['games']
jobs=[]
for g in idx:
    p=g['source'].split('/')
    if p[-3] in ('v87-r2','v88-r2','v89-r2','v95-r2','v86-r2','v91-r2'):
        jobs.append((p[-3]+'/'+p[-2], D+g['dir'], 0 if g['source'].endswith('-a.repl26a') else 1))
def run(j):
    try: return (j[0], hordash.dashes(j[1], j[2]))
    except Exception as e: return (j[0], [])
def report(G):
    for k in sorted(G):
        for side in ('us','op'):
            L=[x for x in G[k] if x[0]==side]
            if not L: continue
            lo=[x for x in L if x[1]<0.6]; hi=[x for x in L if x[1]>=0.6]
            f=lambda S: f"n={len(S)} die{hordash.W}={sum(x[2] for x in S)/max(1,len(S)):.2f} kills={sum(x[3] for x in S)/max(1,len(S)):.2f}"
            print(f"{k:22} {side} share<0.6 {len(lo)/len(L):.2f} | <0.6: {f(lo)} | >=0.6: {f(hi)}")
if __name__=='__main__':
    with Pool(32) as p: res=p.map(run,jobs,chunksize=8)
    G=collections.defaultdict(list)
    for k,o in res: G[k]+=o
    report(G)
