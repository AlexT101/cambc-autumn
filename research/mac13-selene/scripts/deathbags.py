import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    cn={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    win=meta['result']['winner']; res=Counter()
    for e in ev:
        if e['k']=='death':
            v=e['v']; w='W' if team[v]==win else 'L'; nm=cn[v]
            res[(nm,w,'n')]+=1; res[(nm,w,'gems')]+=e['gems']
            res[('ALL',w,'n')]+=1; res[('ALL',w,'gems')]+=e['gems']
            if e.get('by') is None or e['by'] not in team: res[('ALL',w,'campgems')]+=e['gems']
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    n=len(dirs)
    for nm in sorted(set(k[0] for k in tot)):
        print('%-12s'%nm[:12], *('%s deaths %.2f gems %.0f'%(w, tot[(nm,w,'n')]/n, tot[(nm,w,'gems')]/n) for w in 'WL'))
    print('camp-killed gems W %.1f L %.1f'%(tot[('ALL','W','campgems')]/n, tot[('ALL','L','campgems')]/n))
if __name__=='__main__': main()
