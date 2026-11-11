import json,gzip,glob,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json'))
    w=M['result']['winner']; rounds=M['result']['rounds']
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    C=R['champions']
    first={}
    for i,r in enumerate(R['round']):
        for t in (0,1):
            if t in first: continue
            sc=R['gems'][t][i]
            tot=sc+sum(c['gems'][i] for c in C if c['team']==t and c['alive'][i])
            if tot>=1000: first[t]=r
    if not first: return None
    t0=min(first,key=lambda t:first[t])
    return dict(first_team=t0, first_round=first[t0], other=first.get(1-t0), won=(w==t0), end=rounds, lag=rounds-first[t0])
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    res=[]
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one,dirs):
            if o: res.append(o)
    print(len(res),'games with a potential win; first-to-potential wins %.1f%%'%(100*sum(r['won'] for r in res)/len(res)))
    print('lag from potential to game end: median',st.median(r['lag'] for r in res),'mean %.0f'%st.mean(r['lag'] for r in res))
    lost=[r for r in res if not r['won']]
    print('when first-to-potential lost: lag median', st.median(r['lag'] for r in lost) if lost else None, len(lost))
    b=collections.Counter(min(r['lag']//25*25,300) for r in res); print(sorted(b.items()))
if __name__=='__main__': main()
