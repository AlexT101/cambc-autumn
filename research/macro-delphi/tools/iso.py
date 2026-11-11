import json,gzip,glob,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    C=R['champions']
    out=collections.Counter()
    for t in (0,1):
        P=[c for c in C if c['team']==t and names[c['id']]=='Prism']
        if not P: continue
        P=P[0]
        for i,r in enumerate(R['round']):
            if r<30 or r>400 or not P['alive'][i]: continue
            ph='early' if r<=150 else 'mid'
            p=(P['x'][i],P['y'][i])
            al=min([cheb(p,(c['x'][i],c['y'][i])) for c in C if c['team']==t and c['id']!=P['id'] and c['alive'][i]] or [99])
            en=sorted([cheb(p,(c['x'][i],c['y'][i])) for c in C if c['team']!=t and c['alive'][i]])
            out[ph,'n']+=1
            out[ph,'ally<=4']+= al<=4
            out[ph,'ally<=8']+= al<=8
            out[ph,'enemy<=8']+= bool(en) and en[0]<=8
            out[ph,'enemy2<=8']+= len(en)>1 and en[1]<=8
            out[ph,'iso_enemy<=8']+= al>8 and bool(en) and en[0]<=8
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one,dirs): agg.update(o)
    for ph in ('early','mid'):
        n=agg[ph,'n']; print(ph, {k[1]: round(v/n,3) for k,v in agg.items() if k[0]==ph})
if __name__=='__main__': main()
