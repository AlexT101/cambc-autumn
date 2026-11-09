import beh, json, sys, pickle, os
from multiprocessing import Pool
# usage: local.py ANA_DIR OUT.pkl BOTIDX   (metrics with T = the team of results bot BOTIDX)
A=sys.argv[1]; OUT=sys.argv[2]; B=int(sys.argv[3])
idx=json.load(open(A+'/index.json'))['games']
jobs=[]
for g in idx:
    s=os.path.basename(g['source'])
    o=s.rsplit('-',1)[1].split('.')[0]  # '12' bot0 is A
    T = (0 if o=='12' else 1) if B==0 else (1 if o=='12' else 0)
    jobs.append((s,g['dir'],T))
def run(j):
    s,d,T=j
    try: return ('local','ocean',s,beh.metrics(A+'/'+d,T))
    except Exception as e: return ('local','ocean',s,None)
if __name__=='__main__':
    with Pool(32) as p: res=p.map(run,jobs,chunksize=8)
    pickle.dump(res,open(OUT,'wb')); print(len(res), sum(r[3] is None for r in res))
