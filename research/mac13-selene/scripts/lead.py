import json, gzip, sys, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
    except Exception: return None
    win=meta['result']['winner']; out=[]
    g=R['gems']  # per round [a,b]?
    for rr in (200,300,400,500,600):
        if rr-1<len(g[0]):
            a,b=g[0][rr-1],g[1][rr-1]
            # bags carried
            bag=[0,0]
            for c in R['champions']:
                if c['alive'][rr-1]: bag[c['team']]+=c['gems'][rr-1]
            out.append((rr,a-b,bag[0]-bag[1],int(win==0)))
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    bins=[(-9999,-200),(-200,-100),(-100,-50),(-50,50),(50,100),(100,200),(200,9999)]
    for rr in (200,300,400,500,600):
        s=[x for x in rows if x[0]==rr]
        line=[]
        for lo,hi in bins:
            v=[x[3] for x in s if lo<=x[1]<hi]
            line.append('%d..%d: %.0f%% (%d)'%(lo,hi,100*sum(v)/max(1,len(v)),len(v)))
        print('r%d tributed lead A-B'%rr,' | '.join(line))
    for rr in (300,500):
        s=[x for x in rows if x[0]==rr]
        line=[]
        for lo,hi in bins:
            v=[x[3] for x in s if lo<=x[1]+x[2]<hi]
            line.append('%d..%d: %.0f%% (%d)'%(lo,hi,100*sum(v)/max(1,len(v)),len(v)))
        print('r%d tributed+bags lead'%rr,' | '.join(line))
if __name__=='__main__': main()
