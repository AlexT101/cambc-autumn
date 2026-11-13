import json, gzip, sys, os
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}
    idx={c['id']:i for i,c in enumerate(R['champions'])}
    rix={r:i for i,r in enumerate(R['round'])}
    out=[]
    shops=defaultdict(list)
    for e in ev:
        if e['k']=='shop': shops[e['a']].append(e['r'])
    starts={}
    for e in ev:
        if e['k']=='recall_start': starts[e['a']]=e['r']
        if e['k']=='recall_end':
            a=e['a']; r0=starts.get(a,e['r']-5)
            c=R['champions'][idx[a]]; i=rix.get(r0-1, rix.get(r0))
            if i is None: continue
            hpf=c['hp'][i]/c['maxHp'][i] if c['maxHp'][i] else 1
            shopped=any(e['r']<=s<=e['r']+3 for s in shops[a])
            out.append((names[a], hpf, c['gold'][i], c['gems'][i], shopped))
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[]
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r: rows+=r
    print('recalls',len(rows),'per team-game',len(rows)/len(dirs)/2)
    b=Counter()
    for nm,h,g,gm,sh in rows:
        hb='hp<.4' if h<.4 else ('hp<.7' if h<.7 else ('hp<.95' if h<.95 else 'full'))
        b[(hb, 'gold>=30' if g>=30 else 'gold<30', 'gems' if gm>0 else 'nogems', 'shop' if sh else 'noshop')]+=1
    for k,v in b.most_common(): print(k,v)
if __name__=='__main__': main()
