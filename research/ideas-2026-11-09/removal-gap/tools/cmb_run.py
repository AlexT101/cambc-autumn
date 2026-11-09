import cmb, json, collections, sys, os
from multiprocessing import Pool
D='/home/ubuntu/tmp-offload/handoff/gate/analysis/'
def live(vs):
    idx=json.load(open(D+'index.json'))['games']; jobs=[]
    for g in idx:
        p=g['source'].split('/')
        if p[-3] in vs: jobs.append((p[-3]+'/'+p[-2], D+g['dir'], 0 if g['source'].endswith('-a.repl26a') else 1))
    return jobs
def loc(A, label, B=0):
    idx=json.load(open(A+'/index.json'))['games']; jobs=[]
    for g in idx:
        o=os.path.basename(g['source']).rsplit('-',1)[1].split('.')[0]
        T=(0 if o=='12' else 1) if B==0 else (1 if o=='12' else 0)
        jobs.append((label, A+'/'+g['dir'], T))
    return jobs
def run(j):
    try: return (j[0], cmb.cm(j[1], j[2]))
    except Exception: return (j[0], None)
def report(jobs, keys=None):
    with Pool(32) as p: res=p.map(run,jobs,chunksize=8)
    G=collections.defaultdict(list)
    for k,f in res:
        if f: G[k].append(f)
    allk=sorted(set().union(*[set(f) for L in G.values() for f in L]))
    if keys: allk=[k for k in allk if any(k.startswith(x) for x in keys)]
    labs=sorted(G)
    print('metric'.ljust(24)+''.join(f'{l[-16:]:>17}' for l in labs))
    print('n'.ljust(24)+''.join(f'{len(G[l]):>17}' for l in labs))
    for k in allk:
        print(k.ljust(24)+''.join(f'{sum(f.get(k,0) for f in G[l])/len(G[l]):>17.2f}' for l in labs))
    return G
if __name__=='__main__':
    jobs=live(['v87-r2','v89-r2','v91-r2'])+loc(sys.argv[1],'local-rm1(us)')
    report(jobs)
