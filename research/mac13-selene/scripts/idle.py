# Per alive champion-round: active (moved / attacked / cast / channel) vs idle; idle split by enemy in sight.
import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    cn={c['id']:c['name'] for c in meta['champions']}
    act=set()
    for e in ev:
        if e['k'] in ('attack','cast','move') and 'a' in e: act.add((e['r'],e['a']))
    res=Counter()
    for c in R['champions']:
        nm='Prism' if cn[c['id']]=='Prism' else 'other'
        for i,r in enumerate(R['round']):
            if not c['alive'][i]: continue
            res[(nm,'alive')]+=1
            if (r,c['id']) in act: res[(nm,'active')]+=1
            elif c['chan'][i]: res[(nm,'chan')]+=1
            else:
                res[(nm,'idle')]+=1
                if c['sees'][i]: res[(nm,'idle_seen')]+=1
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps'][:300]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: tot.update(r)
    for nm in ('Prism','other'):
        a=tot[(nm,'alive')]
        print(nm, *('%s %.1f%%'%(k,100*tot[(nm,k)]/a) for k in ('active','chan','idle','idle_seen')))
if __name__=='__main__': main()
