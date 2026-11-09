import os
import gzip, json, sys, collections, os, re
from pathlib import Path
from multiprocessing import Pool
def scan(args):
    d,T=args; d=Path(d)
    meta=json.load(open(d/'meta.json')); team={c['id']:c['team'] for c in meta['champions']}
    rd=json.load(gzip.open(d/'rounds.json.gz')); R=rd['round']; ri={r:i for i,r in enumerate(R)}
    ch={c['id']:c for c in rd['champions']}
    out=[]; starts={}
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='tribute_start' and team.get(e['a'])!=T: starts[e['a']]=e['r']
        if e['k']=='tribute_cancel' and team.get(e['a'])!=T and e.get('cause')=='manual':
            i=ri.get(e['r']-1, ri.get(e['r'])); 
            if i is None: continue
            me=ch[e['a']]; x,y=me['x'][i],me['y'][i]
            if x is None: continue
            ds=[max(abs(c['x'][i]-x),abs(c['y'][i]-y)) for c in rd['champions'] if c['team']==T and c['x'][i] is not None]
            out.append((e['r'], min(ds) if ds else 99, e['r']-starts.get(e['a'],e['r']), e.get('gems',0)))
    return out
def summ(name, rows):
    n=len(rows); 
    if not n: print(name,'none'); return
    near=sum(r[1]<=5 for r in rows); held=sum(r[2]<=1 for r in rows)
    print(f"{name}: {n} manual cancels; nearest of ours <=5 tiles {100*near/n:.0f}%, <=8 {100*sum(r[1]<=8 for r in rows)/n:.0f}%; cancelled within 1 round of start {100*held/n:.0f}%; median gems {sorted(r[3] for r in rows)[n//2]}")
