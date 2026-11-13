"""Champion kills: victim-side bodies vs killer-side bodies within R of the victim, the round before the death.
Also: of victim-side allies within R2 (not within R), how many there were (could have come)."""
import json, gzip, glob, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; R1=6; R2=14
CH=json.load(open(ROOT+'/enums.json'))['champions']
def one(d):
    meta=json.load(open(d+'/meta.json')); team={c['id']:c['team'] for c in meta['champions']}
    typ={c['id']:CH[c['type']] for c in meta['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; ri={r:i for i,r in enumerate(rounds)}
    ci={c['id']:c for c in R['champions']}
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('by') is None or e.get('linked'): continue
        v=e['v']; i=ri.get(e['r']-1)
        if i is None: continue
        c=ci[v]; x,y=c['x'][i],c['y'][i]
        if x is None: continue
        a=en=far=0
        for o in R['champions']:
            if o['id']==v or not o['alive'][i] or o['x'][i] is None: continue
            dd=max(abs(o['x'][i]-x),abs(o['y'][i]-y))
            if o['team']==team[v]:
                if dd<=R1: a+=1
                elif dd<=R2: far+=1
            elif dd<=R1: en+=1
        out.append((a,en,far,typ[v],e['r'],meta['result']['winner']==team[v]))
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[x for o in ex.map(one,ds,chunksize=8) for x in o]
    N=len(S); print('kills',N)
    c=collections.Counter((min(a,3),min(en,4)) for a,en,far,t,r,w in S)
    for k,v in sorted(c.items()): print(' victim-side %d other allies, %d enemies within %d: %5d %.1f%%'%(k[0],k[1],R1,v,100*v/N))
    out=[s for s in S if s[1]>s[0]+1]
    print('outnumbered (enemies >= allies+2):',len(out)/N,' of those with an ally 7-14 away:',sum(1 for s in out if s[2]>0)/len(out))
    print('mean far allies when outnumbered', sum(s[2] for s in out)/len(out))
