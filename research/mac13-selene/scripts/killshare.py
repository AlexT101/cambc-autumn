import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    cn={c['id']:c['name'] for c in meta['champions']}; tm={c['id']:c['team'] for c in meta['champions']}
    res=Counter()
    for c in meta['champions']: res[('present',c['name'])]+=1
    for e in ev:
        if e['k']=='death' and e.get('by') in cn:
            res[('kill',cn[e['by']])]+=1; res['kills']+=1
            for a in e.get('assists',[]):
                if a in cn: res[('assist',cn[a])]+=1
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    print('type, kills per champion-game, assists per champion-game')
    for nm in sorted(set(k[1] for k in tot if isinstance(k,tuple))):
        p=tot[('present',nm)]
        print('%-12s %5d  kills %.2f  assists %.2f'%(nm[:12],p,tot[('kill',nm)]/p,tot[('assist',nm)]/p))
if __name__=='__main__': main()
