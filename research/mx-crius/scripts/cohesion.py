"""Does cohesion predict the result? At rounds T, per team: mean over alive champions of the distance to the nearest
alive ally (Cassi/Issac counted as bodies), mean distance to own spawn centre, gem position (tributed+carried).
Win rate by sign of the cohesion difference, within gem-lead bins."""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; TS=[100,200,300,400,500]
def one(d):
    meta=json.load(open(d+'/meta.json')); w=meta['result']['winner']
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']
    out=[]
    sc=[((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2) for s in mp['spawn']]
    for T in TS:
        if T not in rounds: continue
        i=rounds.index(T); row={}
        for t in (0,1):
            ps=[(c['x'][i],c['y'][i]) for c in R['champions'] if c['team']==t and c['alive'][i] and c['x'][i] is not None]
            val=R['gems'][t][i]+sum((c['gems'][i] or 0) for c in R['champions'] if c['team']==t)
            if len(ps)<2: nn=None
            else: nn=sum(min(max(abs(a[0]-b[0]),abs(a[1]-b[1])) for b in ps if b is not a) for a in ps)/len(ps)
            fwd=sum(max(abs(p[0]-sc[t][0]),abs(p[1]-sc[t][1])) for p in ps)/max(1,len(ps))
            row[t]=(nn,val,fwd,len(ps))
        out.append((T,row,w,max(mp['width'],mp['height'])))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    for T in TS:
        tab=collections.defaultdict(lambda:[0,0])
        for t_,row,w,size in S:
            if t_!=T or row[0][0] is None or row[1][0] is None: continue
            # team 0 view
            dv=row[0][1]-row[1][1]; dn=row[0][0]-row[1][0]
            gb='lead<-25' if dv< -25 else 'lead>25' if dv>25 else 'level'
            cb='tighter' if dn< -2 else 'looser' if dn>2 else 'same'
            tab[(gb,cb)][0]+=1; tab[(gb,cb)][1]+= (w==0)
        print('round',T, ' '.join('%s/%s %d %.0f%%'%(g,c,n,100*x/n) for (g,c),(n,x) in sorted(tab.items()) if n>20))
