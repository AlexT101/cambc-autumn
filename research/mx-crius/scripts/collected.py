import json,gzip,glob,os,sys,statistics as st
from concurrent.futures import ProcessPoolExecutor
R=sys.argv[1]
def one(p):
    d=os.path.dirname(p); m=json.load(open(p)); w=m['result']['winner']
    RR=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(RR['round'])}
    out={}
    for T in (150,300,600):
        i=ri.get(T)
        if i is None: continue
        for t in (0,1):
            v=RR['gems'][t][i]+sum((c['gems'][i] or 0) for c in RR['champions'] if c['team']==t)
            # gems collected = tributed + carried + lost to deaths so far is not tracked here (wealth)
            out[(T,'W' if t==w else 'L')]=v
    return out
if __name__=='__main__':
    ps=glob.glob(R+'/*/meta.json')
    with ProcessPoolExecutor(32) as ex: S=list(ex.map(one,ps,chunksize=8))
    for T in (150,300,600):
        for k in 'WL':
            xs=[s[(T,k)] for s in S if (T,k) in s]
            print(T,k,'wealth mean %.0f (n=%d)'%(st.mean(xs),len(xs)))
