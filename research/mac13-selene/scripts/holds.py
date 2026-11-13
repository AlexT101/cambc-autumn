import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def cls(g):
    t=g['types']; return 'mono' if 'Monolith' in t else 'golem' if 'Golem' in t else 'elk' if 'Elk' in t else 'wolf' if 'Wolf' in t else 'gems' if 'Gem cluster' in t else 'gold'
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz'))); ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    G={g['id']:g for g in mp['groups']}; tile={}
    for g in mp['groups']:
        for t in g['tiles']: tile[tuple(t)]=g['id']
    res=Counter()
    # champion-rounds standing on a camp tile of a group in state 2 (cleared, awaiting capture)
    rows=R['groups']; j=0; cur={}
    n=len(R['round'])
    for i,r in enumerate(R['round']):
        while j<len(rows) and rows[j][0]<=r: cur[rows[j][1]]=rows[j][2]; j+=1
        for c in R['champions']:
            if not c['alive'][i] or c['x'][i] is None: continue
            g=tile.get((c['x'][i],c['y'][i]))
            res['alive']+=1
            if g is not None and cur.get(g)==2: res['hold']+=1; res['hold_'+cls(G[g])]+=1
    for e in ev:
        if e['k']=='capture':
            c=cls(G[e['g']]); res['cap_'+c]+=1; res['holders_'+c]+=len(e['shares'])
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps'][:300]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: tot.update(r)
    print('hold share of alive champion-rounds %.1f%%'%(100*tot['hold']/tot['alive']))
    for c in ['wolf','gems','gold','elk','golem','mono']:
        k=tot['cap_'+c] or 1
        print(c,'captures/game %.1f holders/capture %.2f hold champion-rounds/capture %.1f'%(tot['cap_'+c]/300,tot['holders_'+c]/k,tot['hold_'+c]/k))
if __name__=='__main__': main()
