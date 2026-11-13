"""For champion kills: rounds from the victim's first champion damage (within 20 rounds before) to death; for victim-side
allies 7-14 away at engagement start, their distance change by death; the victim's distance to spawn trend."""
import json, gzip, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def one(d):
    meta=json.load(open(d+'/meta.json')); team={c['id']:c['team'] for c in meta['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; ri={r:i for i,r in enumerate(rounds)}
    ci={c['id']:c for c in R['champions']}
    hits=collections.defaultdict(list); out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); k=e['k']
        if k in('attack','cast') and e.get('dmg'):
            for v,a in e['dmg']:
                if v in team and team[v]!=team.get(e['a']): hits[v].append(e['r'])
        if k=='death' and e.get('by') is not None and not e.get('linked'):
            v=e['v']; r=e['r']; hs=[h for h in hits[v] if r-20<=h<=r]
            if not hs: continue
            r0=min(hs)
            # extend back: chain of hits with gaps <=3
            hs2=sorted(set(h for h in hits[v] if h<=r),reverse=True); s=r
            for h in hs2:
                if s-h<=3: s=h
                else: break
            i0=ri.get(s-1); i1=ri.get(r-1)
            if i0 is None or i1 is None: continue
            V=ci[v]
            if V['x'][i0] is None: continue
            far=[]
            for o in R['champions']:
                if o['team']!=team[v] or o['id']==v or not o['alive'][i0] or o['x'][i0] is None or o['x'][i1] is None: continue
                d0=max(abs(o['x'][i0]-V['x'][i0]),abs(o['y'][i0]-V['y'][i0]))
                if 7<=d0<=14:
                    vx,vy=(V['x'][i1],V['y'][i1]) if V['x'][i1] is not None else (V['x'][i0],V['y'][i0])
                    d1=max(abs(o['x'][i1]-vx),abs(o['y'][i1]-vy))
                    far.append((d0,d1))
            out.append((r-s,far))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    L=sorted(s[0] for s in S); n=len(L)
    print('kills',n,'engagement length quartiles',L[n//4],L[n//2],L[3*n//4],'p90',L[9*n//10])
    F=[f for s in S for f in s[1]]
    print('far allies',len(F),'closed by mean %.1f; closed>=3: %.2f; opened: %.2f'%(st.mean(a-b for a,b in F),sum(1 for a,b in F if a-b>=3)/len(F),sum(1 for a,b in F if b>a)/len(F)))
