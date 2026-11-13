import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    rix={r:i for i,r in enumerate(R['round'])}
    hit=set()
    for e in ev:
        if e['k'] in('attack','cast') and e.get('camp') is not None: hit.add((e['a'],e['r']))
    res=Counter(); n=len(R['round'])
    for c in R['champions']:
        for i in range(1,n):
            if not c['alive'][i] or c['x'][i] is None: continue
            s='seen' if c['sees'][i] else 'quiet'
            moved=(c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1]) if c['x'][i-1] is not None else False
            res[(s,'r')]+=1
            if (c['id'],R['round'][i]) in hit: res[(s,'camp')]+=1
            elif moved: res[(s,'move')]+=1
            else: res[(s,'still')]+=1
    return res
def main():
    dirs=sorted([os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps'])[:300]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: tot.update(r)
    T=tot[('seen','r')]+tot[('quiet','r')]
    for s in ('seen','quiet'):
        r=tot[(s,'r')]; print(s, 'share %.3f'%(r/T), 'camp %.3f move %.3f still %.3f'%(tot[(s,'camp')]/r, tot[(s,'move')]/r, tot[(s,'still')]/r))
if __name__=='__main__': main()
