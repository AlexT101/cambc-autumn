# Timeline of one decoded scrim game: every 50 rounds, owned/tributed/alive/kills/captures for us vs them.
import json,gzip,sys,os,collections,numpy as np
ana=os.path.expanduser('~/tmp-offload/bigl/ana'); games=json.load(open(os.path.expanduser('~/tmp-offload/bigl/games.json')))
idx=json.load(open(ana+'/index.json'))['games']
mp=sys.argv[1]; opp=sys.argv[2] if len(sys.argv)>2 else 'Fish'; side=sys.argv[3] if len(sys.argv)>3 else None
for g in idx:
    m=os.path.basename(g['source']).split('.')[0]; gm=games.get(m)
    if gm and gm['map']==mp and opp in gm['opp_name'] and (side is None or gm['side']==side): break
d=ana+'/'+g['dir']; meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
us=0 if gm['side']=='a' else 1
print(mp,gm['opp_name'],gm['side'],gm['result'],gm['rounds'],gm['our_picks'],gm['opp_picks'])
team={c['id']:c['team'] for c in meta['champions']}; nm={c['id']:c['name'][:5]+('*' if c['team']==us else '') for c in meta['champions']}
cap=collections.defaultdict(lambda:[0,0]); kill=collections.defaultdict(lambda:[0,0]); kx=collections.defaultdict(lambda:[0,0]); dc=collections.defaultdict(lambda:[0,0])
for e in ev:
    b=e['r']//50*50
    if e['k']=='capture':
        for cid,gems,gold in e['shares']: cap[b][team[cid]!=us]+=gems
    if e['k']=='death':
        vt=team[e['v']]
        if e.get('by') is not None and not e.get('linked'): kill[b][team[e['by']]!=us]+=1
        if e.get('by') is None: dc[b][vt!=us]+=1
        kx[b][vt!=us]+=e.get('gems',0)
trib=np.array(R['gems']); car=np.zeros((2,len(R['round'])))
for c in R['champions']: car[c['team']]+=np.array(c['gems'])
print('round  trib me/op   carried me/op  cap me/op  kills me/op  gems-died me/op  campdeaths')
for i in range(49,len(R['round']),50):
    b=(i+1)//50*50-50
    print(f"{R['round'][i]:5d} {trib[us][i]:5.0f}/{trib[1-us][i]:5.0f}  {car[us][i]:5.0f}/{car[1-us][i]:5.0f}   {cap[b][0]:4d}/{cap[b][1]:4d}   {kill[b][0]:2d}/{kill[b][1]:2d}   {kx[b][0]:4d}/{kx[b][1]:4d}  {dc[b]}")
