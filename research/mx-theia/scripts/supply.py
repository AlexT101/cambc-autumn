# Supply use by side: per game, for each group (in team-relative side), potential captures = rounds/(respawn+10)
# vs actual captures by each team. Gem-weighted.
import json,gzip,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
idx=json.load(open(ROOT+'/index.json'))
dirs=sorted(set(g['dir'] for g in idx['games']))
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception: return None
    rounds=meta['result']['rounds']; win=meta['result']['winner']
    C=collections.Counter()
    for g in mp['groups']:
        mono='Monolith' in g['types']
        for team in (0,1):
            rel='mid' if g['side']==-1 else 'own' if g['side']==team else 'enemy'
            if mono: rel='mono'
            pot=g['gems']*min(rounds,600)/(g['respawn']+10)
            C[('pot',int(team==win),rel)]+=pot
    for e in ev:
        if e['k']=='capture' and e['r']<=600:
            g=next((x for x in mp['groups'] if x['id']==e['g']),None)
            if g is None: continue
            team=e['team']; mono='Monolith' in g['types']
            rel='mid' if g['side']==-1 else 'own' if g['side']==team else 'enemy'
            if mono: rel='mono'
            C[('got',int(team==win),rel)]+=sum(s[1] for s in e['shares'])
    return C
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,dirs,chunksize=4) if r]
    T=collections.Counter()
    for r in res: T.update(r)
    n=len(res)
    for w in (1,0):
        for rel in ('own','mid','enemy','mono'):
            print('W' if w else 'L', rel, 'potential/game %.0f'%(T[('pot',w,rel)]/n), 'got %.0f'%(T[('got',w,rel)]/n), 'use %.2f'%(T[('got',w,rel)]/max(1,T[('pot',w,rel)])))
