import json, gzip, sys, os
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def cls(g):
    t=g['types']
    return 'mono' if 'Monolith' in t else 'golem' if 'Golem' in t else 'elk' if 'Elk' in t else 'wolf' if 'Wolf' in t else 'gems' if 'Gem cluster' in t else 'gold'
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    win=meta['result']['winner']; rounds=meta['result']['rounds']
    G={g['id']:g for g in mp['groups']}
    res=Counter()
    for g in G.values():
        c=cls(g); res[(c,'groups')]+=1; res[(c,'supply')]+=rounds/max(1,g['respawn']+10)*g['gems']
    for e in ev:
        if e['k']=='capture':
            g=G[e['g']]; c=cls(g); gems=sum(s[1] for s in e['shares'])
            w='W' if e['team']==win else 'L'
            res[(c,'cap'+w)]+=gems
            # side: 'side' field = which team's half? 
            sd=g.get('side'); own = 'own' if sd==e['team'] else ('mid' if sd not in (0,1) else 'enemy')
            res[(c,own+w)]+=gems
    res['rounds']+=rounds
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: tot.update(r)
    n=len(dirs)
    print('per game; supply = rounds/(respawn+10)*gems summed over groups (both teams)')
    for c in ['wolf','gems','gold','elk','golem','mono']:
        print('%-6s groups %.1f supply %6.0f  capW %5.0f capL %5.0f  util %.0f%%  | ownW %.0f ownL %.0f midW %.0f midL %.0f enW %.0f enL %.0f'%(c,tot[(c,'groups')]/n,tot[(c,'supply')]/n,tot[(c,'capW')]/n,tot[(c,'capL')]/n,100*(tot[(c,'capW')]+tot[(c,'capL')])/max(1,tot[(c,'supply')]),
          *(tot[(c,k)]/n for k in ['ownW','ownL','midW','midL','enemyW','enemyL'])))
if __name__=='__main__': main()
