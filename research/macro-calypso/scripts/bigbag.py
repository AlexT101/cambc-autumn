import gzip, json, sys, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    meta=json.loads((d/'meta.json').read_text()); win=meta['result']['winner']
    R=json.load(gzip.open(d/'rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}; team={c['id']:c['team'] for c in ch}
    out=[]
    tstart={}
    for e in ev:
        if e['k']=='tribute_start': tstart[e['a']]=e
        if e['k']=='death' and e.get('gems',0)>=200 and 'linked' not in e:
            v=e['v']; c=ch[idx[v]]; r=e['r']; rr=max(0,r-1); t=team[v]
            chan=c['chan'][rr]
            def near(tm,rad=8):
                return sum(1 for o in ch if o['team']==tm and o['id']!=v and o['alive'][rr] and o['x'][rr] is not None and cheb((o['x'][rr],o['y'][rr]),e['at'])<=rad)
            ts=tstart.get(v); tr=(r-ts['r']) if ts and r-ts['r']<300 else None
            out.append(dict(gems=e['gems'],won=t==win,chan=chan,allies=near(t),enemies=near(1-t),since_trib_start=tr,r=r))
    return out
if __name__=='__main__':
    dirs=sorted(p.parent for p in Path(sys.argv[1]).glob('*/meta.json'))
    with ProcessPoolExecutor(32) as ex: res=[x for r in ex.map(one,dirs) for x in r]
    print(len(res))
    print('chan', collections.Counter(x['chan'] for x in res))
    print('allies', collections.Counter(x['allies'] for x in res))
    print('enemies', collections.Counter(x['enemies'] for x in res))
    print('since trib start', sorted(collections.Counter(x['since_trib_start'] for x in res if x['since_trib_start'] is not None).items())[:30])
