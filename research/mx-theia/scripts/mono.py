# Monolith captures: round, capturer W/L, wealth lead before (tributed+carried), and win rate of the first capturer.
import json,gzip,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
idx=json.load(open(ROOT+'/index.json'))
dirs=sorted(set(g['dir'] for g in idx['games']))
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]; R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    mono={g['id'] for g in mp['groups'] if 'Monolith' in g['types']}
    if not mono: return ('none',)
    win=meta['result']['winner']; CH=R['champions']
    def wealth(t,i): return R['gems'][t][i]+sum((c['gems'][i] or 0) for c in CH if c['team']==t)
    caps=[]
    for e in ev:
        if e['k']=='capture' and e['g'] in mono and e['team'] in (0,1):
            i=max(0,e['r']-31); t=e['team']
            caps.append((e['r'],int(t==win),wealth(t,i)-wealth(1-t,i)))
    nm=len(mono)
    return ('mono',nm,caps,meta['result']['rounds'])
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,dirs,chunksize=4) if r]
    m=[r for r in res if r[0]=='mono']
    print('games',len(res),'with monolith',len(m))
    first=[r[2][0] for r in m if r[2]]
    print('games with a mono capture',len(first),'first capturer wins',sum(x[1] for x in first)/max(1,len(first)))
    print('first capture round median',statistics.median(x[0] for x in first))
    for lo,hi in ((0,300),(300,600),(600,900),(900,2001)):
        s=[x for x in first if lo<=x[0]<hi]
        if s: print(f' first in r{lo}-{hi}: n={len(s)} wins {sum(x[1] for x in s)/len(s):.2f} lead30before mean {statistics.mean(x[2] for x in s):.0f}; lead<=0: n={sum(x[2]<=0 for x in s)} wins {sum(x[1] for x in s if x[2]<=0)/max(1,sum(x[2]<=0 for x in s)):.2f}')
    allc=[c for r in m for c in r[2]]
    print('all mono captures',len(allc),'by eventual winner',sum(c[1] for c in allc)/len(allc))
    print('mono groups per map', collections.Counter(r[1] for r in m))
