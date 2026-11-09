import beh, json, sys, collections, pickle
from multiprocessing import Pool
D='/home/ubuntu/tmp-offload/handoff/gate/analysis/'
idx=json.load(open(D+'index.json'))['games']
jobs=[]
for g in idx:
    s=g['source']
    parts=s.split('/')
    if not parts[-3].endswith('-r2'): continue
    v=parts[-3]; opp=parts[-2]; T=0 if s.endswith('-a.repl26a') else 1
    jobs.append((v,opp,g['map'],g['dir'],T))
def run(j):
    v,opp,m,d,T=j
    try: return (v,opp,m,beh.metrics(D+d,T))
    except Exception as e: return (v,opp,m,None)
if __name__=='__main__':
    with Pool(32) as p: res=p.map(run,jobs,chunksize=8)
    pickle.dump(res,open('/tmp/claude-1000/-home-ubuntu-cambc-autumn/b97d3167-6ed0-42c1-a130-a3dd315c87de/scratchpad/gap/live.pkl','wb'))
    print(len(res), sum(r[3] is None for r in res))
