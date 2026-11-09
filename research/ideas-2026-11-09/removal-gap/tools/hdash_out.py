import pickle, json, gzip, os, collections, beh
A='/tmp/claude-1000/-home-ubuntu-cambc-autumn/b97d3167-6ed0-42c1-a130-a3dd315c87de/scratchpad/gap/ana-dbg-hor'
rows=pickle.load(open('/tmp/claude-1000/-home-ubuntu-cambc-autumn/b97d3167-6ed0-42c1-a130-a3dd315c87de/scratchpad/gap/hdash.pkl','rb'))
idx=json.load(open(A+'/index.json'))['games']; by={os.path.basename(g['source']):g['dir'] for g in idx}
cache={}
def game(f):
    if f not in cache:
        meta,rd,ev=beh.load(A+'/'+by[f]); T=0 if f.endswith('-12.repl26a') else 1
        hor=[c['id'] for c in meta['champions'] if c['name']=='Heart of Ruin' and c['team']==T]
        deaths=collections.defaultdict(list)
        for e in ev:
            if e['k']=='death': deaths[e['v']].append(e['r'])
        team={c['id']:c['team'] for c in meta['champions']}
        cache[f]=(hor,deaths,team)
    return cache[f]
G=collections.defaultdict(lambda:[0,0,0])
for f,r,h,fr,v,dec,leth in rows:
    hor,deaths,team=game(f)
    hid=h if h in hor else (hor[0] if len(hor)==1 else None)
    if hid is None: continue
    died=any(r<=d<=r+4 for d in deaths[hid])
    ekill=sum(1 for c,t in team.items() if t!=team[hid] and any(r<=d<=r+4 for d in deaths[c]))
    k=(dec,'lo' if fr<0.6 else 'hi','v<500' if v<500 else 'v>=500')
    G[k][0]+=1; G[k][1]+=died; G[k][2]+=ekill
for k in sorted(G):
    n,d,kk=G[k]; print(k, n, f'die4 {d/n:.2f} enemy deaths4 {kk/n:.2f}')
