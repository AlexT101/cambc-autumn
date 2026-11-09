import lockcut, json, pickle, sys, os
from multiprocessing import Pool
D='/home/ubuntu/tmp-offload/handoff/gate/analysis/'
def jl():
    idx=json.load(open(D+'index.json'))['games']; jobs=[]
    for g in idx:
        s=g['source']; p=s.split('/')
        if not p[-3].endswith('-r2'): continue
        jobs.append((p[-2], D+g['dir'], 0 if s.endswith('-a.repl26a') else 1))
    return jobs
def jloc(A, B):
    idx=json.load(open(A+'/index.json'))['games']; jobs=[]
    for g in idx:
        o=os.path.basename(g['source']).rsplit('-',1)[1].split('.')[0]
        T=(0 if o=='12' else 1) if B==0 else (1 if o=='12' else 0)
        jobs.append(('local-T=bot%d'%B, A+'/'+g['dir'], T))
    return jobs
def run(j):
    try: return (j[0], lockcut.cuts(j[1], j[2]))
    except Exception: return (j[0], [])
if __name__=='__main__':
    jobs=jl()+jloc(sys.argv[1],1)+jloc(sys.argv[1],0)
    with Pool(32) as p: res=p.map(run, jobs, chunksize=8)
    import collections
    G=collections.defaultdict(list); n=collections.Counter()
    for k,c in res: G[k]+=c; n[k]+=1
    for k in G:
        c=G[k]; late=[x for x in c if x['left']<=2 and x['dur']>=5]
        def summ(L):
            if not L: return 'none'
            rb=[x for x in L if x['rebank'] is not None]; di=[x for x in L if x['died'] is not None]
            import statistics as st
            return f"n={len(L)} ({len(L)/n[k]:.3f}/game) gems~{st.mean(x['gems'] for x in L):.0f} rebank {len(rb)/len(L):.2f} in med {st.median([x['rebank'] for x in rb]) if rb else -1} rds; died before {len(di)/len(L):.2f} (by T {sum(x.get('killer_team_T',0) for x in di)/max(1,len(di)):.2f}); T wins {st.mean(x['win'] for x in L):.2f}"
        print(k, 'ALL', summ(c)); print(k, 'LATE dur>=5', summ(late))
