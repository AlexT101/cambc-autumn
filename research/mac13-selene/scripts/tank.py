import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
RNG={'Wolf':3,'Elk':4,'Golem':4,'Monolith':5}
RANGED={'Prism','Vesper Vale','Stellar','Tavi','Willow','Cassi'}
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz'))); ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    cn={c['id']:c['name'] for c in meta['champions']}; camps={c['id']:c for c in mp['camps']}
    rix={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    res=Counter()
    for e in ev:
        if e['k']!='camp_attack': continue
        cp=camps.get(e['camp']); 
        if not cp or cp['type'] not in RNG: continue
        t=e['tgt']; i=rix.get(e['r'])
        if t not in C or i is None: continue
        nm=cn[t]; cls='ranged' if nm in RANGED else 'melee'
        res[(cls,'dmg')]+=e['dmg']
        tc=C[t]
        rng=RNG[cp['type']]
        other=False
        for c in R['champions']:
            if c['id']==t or c['team']!=tc['team'] or not c['alive'][i] or c['x'][i] is None: continue
            if cn[c['id']] in RANGED: continue
            d_=max(abs(c['x'][i]-cp['x']),abs(c['y'][i]-cp['y']))
            if d_<=rng: other=True
        if other: res[(cls,'dmg_melee_ally_in_range')]+=e['dmg']
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps'][:400]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: tot.update(r)
    for cls in ('ranged','melee'):
        print(cls,'camp dmg taken per game %.0f, of it with a melee ally also in the camp range %.0f%%'%(tot[(cls,'dmg')]/len(dirs),100*tot[(cls,'dmg_melee_ally_in_range')]/max(1,tot[(cls,'dmg')])))
if __name__=='__main__': main()
