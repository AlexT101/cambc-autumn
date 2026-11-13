import json, gzip, sys, os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}
    team={c['id']:c['team'] for c in meta['champions']}
    win=meta['result']['winner']
    rix={r:i for i,r in enumerate(R['round'])}
    out={}
    capg=defaultdict(int); capgold=defaultdict(int); camphits=defaultdict(int); recalls=defaultdict(int); trib=defaultdict(int)
    for e in ev:
        if e['k']=='capture':
            for cid,gm,gd in e['shares']: capg[cid]+=gm; capgold[cid]+=gd
        elif e['k'] in ('attack','cast') and 'camp' in e: camphits[e['a']]+=1
        elif e['k']=='recall_end': recalls[e['a']]+=1
        elif e['k']=='tribute_end': trib[e['a']]+=e['gems']
    i600=rix.get(600, len(R['round'])-1)
    for c in R['champions']:
        cid=c['id']; n=len(R['round'])
        alive=sum(c['alive']); 
        moved=sum(1 for i in range(1,n) if c['alive'][i] and c['alive'][i-1] and c['x'][i] is not None and c['x'][i-1] is not None and (c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1]))
        out[cid]=dict(name=names[cid], win=int(team[cid]==win), alive=alive, moved=moved/max(1,alive), camphits=camphits[cid]/max(1,alive),
                     capg=capg[cid], capgold=capgold[cid], earned600=c['earned'][i600], deaths=c['deaths'][-1], kills=c['kills'][-1], recalls=recalls[cid], trib=trib[cid], rounds=n)
    return list(out.values())
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    by=defaultdict(list)
    for r in rows: by[r['name']].append(r)
    keys=['moved','camphits','capg','capgold','earned600','deaths','kills','recalls','trib','rounds']
    print('name n '+' '.join(keys))
    for nm,L in sorted(by.items(), key=lambda kv:-len(kv[1])):
        print(f"{nm:14s} {len(L):5d} "+' '.join(f"{sum(r[k] for r in L)/len(L):8.2f}" for k in keys))
if __name__=='__main__': main()
