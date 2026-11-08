# Positions, hp and capture/group events of both teams over the first N rounds of one scrim game.
import json,gzip,os,sys,collections
ana=os.path.expanduser('~/tmp-offload/bigl/ana'); games=json.load(open(os.path.expanduser('~/tmp-offload/bigl/games.json')))
idx=json.load(open(ana+'/index.json'))['games']
mp_,opp,side,N=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4])
for g in idx:
    m=os.path.basename(g['source']).split('.')[0]; gm=games.get(m)
    if gm and gm['map']==mp_ and opp in gm['opp_name'] and gm['side']==side: break
d=ana+'/'+g['dir']; meta=json.load(open(d+'/meta.json')); R=json.load(gzip.open(d+'/rounds.json.gz'))
us=0 if side=='a' else 1
nm={c['id']:(c['name'][:4]+('*' if c['team']==us else '')) for c in meta['champions']}
step=int(sys.argv[5]) if len(sys.argv)>5 else 5
for i in range(0,N,step):
    print(R['round'][i],' '.join(f"{nm[c['id']]}({c['x'][i]},{c['y'][i]}){int(100*c['hp'][i]/c['maxHp'][i])}%g{c['gems'][i]}" for c in R['champions']))
for l in gzip.open(d+'/events.jsonl.gz','rt'):
    e=json.loads(l)
    if e['r']>N: break
    if e['k'] in ('capture','group_clear','capture_hold','death','group_wake'): print(e['r'],e['k'],{k:v for k,v in e.items() if k in ('g','team','by','v','shares','at','gems')})
