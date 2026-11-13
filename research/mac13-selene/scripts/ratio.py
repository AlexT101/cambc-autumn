import json, gzip, sys, os, math
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
    except Exception: return None
    pr={c['team']:c['id'] for c in meta['champions'] if c['name']=='Prism'}
    if len(pr)!=2: return None
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}; rix={r:i for i,r in enumerate(R['round'])}
    out=[]
    for r in (200,300,400):
        i=rix.get(r)
        if i is None: continue
        a=ch[idx[pr[0]]]['gems'][i]+ (0 if ch[idx[pr[0]]]['alive'][i] else 0); b=ch[idx[pr[1]]]['gems'][i]
        out.append((r, (a+20)/(b+20), int(meta['result']['winner']==0)))
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    for R0 in (200,300,400):
        b=defaultdict(lambda:[0,0])
        for r,q,w in rows:
            if r!=R0: continue
            for qq,ww in ((q,w),(1/q,1-w)):
                k='<0.5' if qq<0.5 else '0.5-0.8' if qq<0.8 else '0.8-1.25' if qq<=1.25 else '1.25-2' if qq<=2 else '>2'
                b[k][0]+=ww; b[k][1]+=1
        print(R0, {k:(round(v[0]/v[1],2),v[1]) for k,v in sorted(b.items())})
if __name__=='__main__': main()
