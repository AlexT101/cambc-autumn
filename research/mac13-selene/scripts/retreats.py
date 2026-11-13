import json, gzip, sys, os, re, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
AN='/home/ubuntu/wt/mac13-selene/replays/.analysis'
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        z=zipfile.ZipFile(meta['source'])
    except Exception: return None
    cn={c['id']:c['name'] for c in meta['champions']}
    Dl={}
    for nm in z.namelist():
        if nm.endswith('.stdout'):
            for m in D_RE.finditer(z.read(nm)): Dl[(int(m.group(1)),int(m.group(2)))]=m.group(3).decode()
    res=Counter(); n=len(R['round'])
    for c in R['champions']:
        for i in range(1,n-5):
            if not c['alive'][i]: continue
            r=R['round'][i]
            if Dl.get((r,c['id']))!='R' or not c['sees'][i]: continue
            hp=c['hp'][i]/max(1,c['maxHp'][i])
            hb='<.3' if hp<.3 else '<.6' if hp<.6 else '<.9' if hp<.9 else 'full'
            lost=c['hp'][i]-min(c['hp'][j] for j in range(i,i+6) if c['alive'][j]) if all(c['alive'][j] for j in range(i,i+6)) else 9999
            died=not all(c['alive'][j] for j in range(i,i+6))
            out='died' if died else ('hit' if lost>0.05*c['maxHp'][i] else 'safe')
            res[(hb,out)]+=1
            res[('bag' if c['gems'][i]>=50 else 'nobag', out)]+=1
            res[(cn[c['id']],out)]+=1
    return res
def main():
    idx=json.load(open(os.path.join(AN,'index.json')))
    dirs=[os.path.join(AN,g['dir']) for g in idx['games'] if 'mirdbg' in g['source']][:400]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: tot.update(r)
    keys=sorted(set(k[0] for k in tot))
    for k in keys:
        T=sum(tot[(k,o)] for o in ('died','hit','safe'))
        if T>2000: print(f"{k:14s} {T:7d} died {tot[(k,'died')]/T:.3f} hit {tot[(k,'hit')]/T:.3f} safe {tot[(k,'safe')]/T:.3f}")
if __name__=='__main__': main()
