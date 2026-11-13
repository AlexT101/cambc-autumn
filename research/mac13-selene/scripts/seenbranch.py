import json, gzip, sys, os, re, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
AN='/home/ubuntu/wt/mac13-selene/replays/.analysis'
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
        z=zipfile.ZipFile(meta['source'])
    except Exception: return None
    Dl={}
    for nm in z.namelist():
        if nm.endswith('.stdout'):
            for m in D_RE.finditer(z.read(nm)): Dl[(int(m.group(1)),int(m.group(2)))]=m.group(3).decode()
    hit=set(); champdmg=set()
    for e in ev:
        if e['k'] in('attack','cast'):
            if e.get('camp') is not None: hit.add((e['a'],e['r']))
            if e.get('tgt') is not None or e.get('dmg'): champdmg.add((e['a'],e['r']))
    res=Counter(); n=len(R['round'])
    for c in R['champions']:
        for i in range(1,n):
            if not c['alive'][i]: continue
            r=R['round'][i]; b=Dl.get((r,c['id']))
            if b is None: continue
            s='seen' if c['sees'][i] else 'quiet'
            res[(s,b)]+=1
            if b=='F' and (c['id'],r) in hit: res[(s,'F+camp')]+=1
    return res
def main():
    idx=json.load(open(os.path.join(AN,'index.json')))
    dirs=[os.path.join(AN,g['dir']) for g in idx['games'] if 'mirdbg' in g['source']][:400]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: tot.update(r)
    for s in ('seen','quiet'):
        T=sum(v for k,v in tot.items() if k[0]==s and k[1]!='F+camp')
        print(s, T, ' '.join(f"{k[1]}:{100*v/T:.1f}" for k,v in sorted(tot.items(), key=lambda kv:-kv[1]) if k[0]==s and v/T>0.005))
if __name__=='__main__': main()
