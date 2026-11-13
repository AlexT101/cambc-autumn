import json,gzip,collections
A='/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
idx=json.load(open(A+'index.json'))['games']
C=collections.Counter(); games=0; N=0
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
for d in sorted({r["dir"] for r in idx}):
    m=json.load(open(A+d+'/meta.json')); w=m['result']['winner']
    team={c['id']:c['team'] for c in m['champions']}; typ={c['id']:c['name'] for c in m['champions']}
    pr=[i for i in typ if typ[i]=='Prism']; games+=1
    if not pr: continue
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); rounds=R['round']; ri={x:i for i,x in enumerate(rounds)}
    ch={int(c['id']):c for c in R['champions']}; G=R['gems']
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    altars=list(set(tuple(e['altar']) for e in ev if e['k']=='tribute_start'))
    if not altars: continue
    for e in ev:
        if e['k']!='death' or e['v'] not in pr or e.get('by') is None: continue
        g=e.get('gemsTo',0) or 0
        if g<300 or team[e['v']]==w: continue
        v=e['v']; i=ri.get(e['r']); 
        if i is None: continue
        N+=1; t=team[v]
        j=max(0,i-15)
        pos=lambda o,k:(ch[o]['x'][k],ch[o]['y'][k])
        p0=pos(v,j); p1=pos(v,i-1)
        a=min(altars,key=lambda q:cheb(q,p1))
        C['approaching altar (dist fell over 15r)' if cheb(a,p1)<cheb(a,p0) else ('at altar both' if cheb(a,p1)<=2 else 'not approaching')]+=1
        wealth=G[t][i] if isinstance(G[0],list) else None
        C['bag+wealth>=1000' if wealth is not None and wealth+g>=1000 else 'bag+wealth<1000']+=1
        # enemy bodies within 3 of that altar 15 rounds before (waiting)
        wait=sum(1 for o in ch if team.get(o)!=t and ch[o]['alive'][j] and ch[o]['x'][j] is not None and cheb(pos(o,j),a)<=4)
        C['enemies within 4 of altar @-15: %d'%min(wait,3)]+=1
        al=sum(1 for o in ch if team.get(o)==t and o!=v and ch[o]['alive'][i-1] and ch[o]['x'][i-1] is not None and cheb(pos(o,i-1),p1)<=4)
        C['allies within 4 @-1: %d'%min(al,3)]+=1
        dead_al=sum(1 for o in ch if team.get(o)==t and o!=v and not ch[o]['alive'][i-1])
        C['allies dead @-1: %d'%min(dead_al,3)]+=1
        C['assists %d'%min(len(e.get('assists',[])),3)]+=1
        C['hp@-15 >=.9' if ch[v]['hp'][j]>=.9*ch[v]['maxHp'][j] else 'hp@-15 <.9']+=1
        C['seen by enemy at -15' if ch[v]['seenBy'][j] else 'unseen at -15']+=1
print('games',games,'loser prism 300+ deaths',N)
print(json.dumps(R['gems'][:2] if False else None))
for k,v in sorted(C.items()): print(k,v)
