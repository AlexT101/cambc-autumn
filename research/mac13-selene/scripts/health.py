import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    res=Counter(); cn={c['id']:c['name'] for c in meta['champions']}
    rs={}
    for e in ev:
        if e['k']=='recall_start': rs[e['a']]=e['r']
        if e['k']=='recall_end':
            res[(cn[e['a']],'recalls')]+=1
    for c in meta['champions']:
        s=c['stats']; nm=c['name']
        res[(nm,'n')]+=1; res[(nm,'camp_taken')]+=s['monsterDamageTaken']; res[(nm,'champ_taken')]+=s['championDamageTaken']
        res[(nm,'heal_got')]+=0; res[(nm,'healing')]+=s['healingDone']; res[(nm,'rounds')]+=meta['result']['rounds']
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    print('type n | per 1000 rounds: camp dmg taken, champ dmg taken, recalls completed, healing done')
    for nm in sorted(set(k[0] for k in tot)):
        n=tot[(nm,'n')]; R=tot[(nm,'rounds')]/1000
        print('%-12s %5d %7.0f %7.0f %5.1f %7.0f'%(nm[:12],n,tot[(nm,'camp_taken')]/R,tot[(nm,'champ_taken')]/R,tot[(nm,'recalls')]/R,tot[(nm,'healing')]/R))
if __name__=='__main__': main()
