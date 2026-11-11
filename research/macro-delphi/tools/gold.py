import json,gzip,glob,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    out=collections.defaultdict(list)
    for c in R['champions']:
        k='P' if names[c['id']]=='Prism' else 'o'
        g=[x for x,a in zip(c['gold'],c['alive']) if a]
        if g: out[k].append(st.mean(g))
        # by phase
        n=len(c['gold'])
        for lo,hi in ((0,200),(200,400),(400,800)):
            seg=[x for x,a in zip(c['gold'][lo:hi],c['alive'][lo:hi]) if a]
            if seg: out[k+str(lo)].append(st.mean(seg))
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.defaultdict(list)
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one,dirs):
            for k,v in o.items(): agg[k]+=v
    for k,v in sorted(agg.items()): print(k,'mean unspent gold %.0f median %.0f'%(st.mean(v),st.median(v)))
if __name__=='__main__': main()
