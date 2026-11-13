"""Win rate by the Prism bag difference (ours - theirs) and by team wealth (tributed + bags) difference at round T,
games where both teams have a living Prism with known bags. usage: py bagwin.py EXTRACT"""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; TS=[150,300,450]
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); w=m['result']['winner']; typ={c['id']:CH[c['type']] for c in m['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    P={c['team']:c for c in R['champions'] if typ[c['id']]=='Prism'}
    if len(P)!=2: return []
    out=[]
    for T in TS:
        i=ri.get(T)
        if i is None: continue
        bag=[P[t]['gems'][i] or 0 for t in (0,1)]
        wl=[R['gems'][t][i]+sum(c['gems'][i] or 0 for c in R['champions'] if c['team']==t) for t in (0,1)]
        out.append((T,bag[0]-bag[1],wl[0]-wl[1],w==0))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    for T in TS:
        X=[s for s in S if s[0]==T]
        print('r%d n=%d'%(T,len(X)))
        for lab,j in (('Prism bag diff',1),('team wealth diff',2)):
            row=[]
            for lo,hi in ((-9999,-100),(-100,-50),(-50,-20),(-20,20),(20,50),(50,100),(100,9999)):
                Y=[s for s in X if lo<=s[j]<hi]
                if Y: row.append('[%d,%d) %d %.0f%%'%(lo,hi,len(Y),100*sum(s[3] for s in Y)/len(Y)))
            print('  %-16s'%lab,' | '.join(row))
