import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    d=Path(d)
    try:
        meta=json.loads((d/'meta.json').read_text()); ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    except Exception: return None
    pr={m['id'] for m in meta['champions'] if m['name']=='Prism'}
    if len(pr)!=2: return None
    duel=None
    for e in ev:
        if e['k']=='death' and e['v'] in pr and e.get('by') in pr: duel=e; break
    if not duel: return None
    R=duel['r']; K=duel['by']; V=duel['v']
    o=Counter(); o['n']=1
    for e in ev:
        if e['r']>=R: break
        if e['k']=='capture':
            for cid,gm,gd in e['shares']:
                if cid==K: o['k_cap_gems']+=gm; o['k_cap_gold']+=gd
                if cid==V: o['v_cap_gems']+=gm; o['v_cap_gold']+=gd
        elif e['k']=='death' and 'camp' not in e and not e.get('linked'):
            if e.get('by')==K: o['k_kill_gems']+=e.get('gems',0) or 0; o['k_kills']+=1
            if e.get('by')==V: o['v_kill_gems']+=e.get('gems',0) or 0; o['v_kills']+=1
    return o
if __name__=='__main__':
  dirs=[str(p.parent) for p in Path(sys.argv[1]).glob('*/meta.json')]
  t=Counter()
  with ProcessPoolExecutor(16) as ex:
      for r in ex.map(one,dirs,chunksize=8):
          if r: t.update(r)
  n=t['n']
  for k in sorted(t): print(k, round(t[k]/n,1))
  