import gzip,json,sys,collections,statistics as st
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    w=meta['result']['winner']; n=len(R['round']); sc=R['gems']; ch=R['champions']
    names={int(c['id']):c['name'] for c in meta['champions']}
    first=None
    for i in range(n):
        for t in (0,1):
            car=sum(c['gems'][i] for c in ch if int(c['team'])==t and c['alive'][i])
            if sc[t][i]+car>=1000: first=(t,i); break
        if first: break
    if not first: return None
    t,i0=first
    pr=[c for c in ch if int(c['team'])==t and names[int(c['id'])]=='Prism']
    if not pr or not pr[0]['alive'][i0]: return None
    p=pr[0]
    died=next((i for i in range(i0,n) if not p['alive'][i]),None)
    tribs=[]; 
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['r']>i0 and e.get('a')==int(p['id']) and e['k'] in('tribute_start','tribute_cancel','tribute_end'): tribs.append(e['k'])
    return dict(won=t==w, died=died is not None, died_after=(died-i0) if died else None, bag=p['gems'][i0], starts=tribs.count('tribute_start'), cancels=tribs.count('tribute_cancel'), ends=tribs.count('tribute_end'), conv=n-i0)
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res=[r for r in ex.map(g,dirs,chunksize=8) if r]
    for lab,S in [('won',[r for r in res if r['won']]),('lost',[r for r in res if not r['won']])]:
        print(lab,len(S),'prism died after reach',round(sum(r['died'] for r in S)/len(S),2),'median rounds to death',st.median([r['died_after'] for r in S if r['died']] or [0]),
              'tribute starts mean',round(st.mean(r['starts'] for r in S),1),'cancels',round(st.mean(r['cancels'] for r in S),1),'conv median',st.median(r['conv'] for r in S))
    W=[r for r in res if r['won']]
    print('won: conversion rounds quartiles', [sorted(r['conv'] for r in W)[int(len(W)*q)] for q in (0.25,0.5,0.75,0.9)])
