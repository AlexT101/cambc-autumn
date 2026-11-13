import json,gzip,collections
A='/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
idx=json.load(open(A+'index.json'))['games']
C=collections.defaultdict(lambda:[0,0]); games=0; gp=0
bagtime=collections.defaultdict(list)
def add(k,g): C[k][0]+=1; C[k][1]+=g
for d in sorted({r["dir"] for r in idx}):
    m=json.load(open(A+d+'/meta.json')); w=m['result']['winner']
    team={c['id']:c['team'] for c in m['champions']}; typ={c['id']:c['name'] for c in m['champions']}
    pr=[i for i in typ if typ[i]=='Prism']
    games+=1
    if not pr: continue
    gp+=1
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); rounds=R['round']; ri={x:i for i,x in enumerate(rounds)}
    ch={int(c['id']):c for c in R['champions']}
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    altars=set(tuple(e['altar']) for e in ev if e['k']=='tribute_start')
    lastend={}
    for p in pr:
        side='W' if team[p]==w else 'L'
        g=[x for x,a in zip(ch[p]['gems'],ch[p]['alive']) if a]
        bagtime[side].append(sum(g)/max(1,len(g)))
    for e in ev:
        if e['k']=='tribute_end': lastend[e['a']]=e['r']
        if e['k']!='death' or e['v'] not in pr or e.get('by') is None: continue
        v=e['v']; g=e.get('gemsTo',0) or 0
        if g<50: continue
        side='W' if team[v]==w else 'L'
        i=ri.get(e['r'])
        if i is None: continue
        x,y=e['at']
        def near(t,rad,j):
            return sum(1 for o,c in ch.items() if team.get(o)==t and o!=v and c['alive'][j] and c['x'][j] is not None and max(abs(c['x'][j]-x),abs(c['y'][j]-y))<=rad)
        for lag in (10,):
            j=max(0,i-lag)
            px,py=ch[v]['x'][j],ch[v]['y'][j]
            al=sum(1 for o,c in ch.items() if team.get(o)==team[v] and o!=v and c['alive'][j] and c['x'][j] is not None and max(abs(c['x'][j]-px),abs(c['y'][j]-py))<=5)
            en=sum(1 for o,c in ch.items() if team.get(o)!=team[v] and c['alive'][j] and c['x'][j] is not None and max(abs(c['x'][j]-px),abs(c['y'][j]-py))<=8)
            add(('allies5@-10',side,min(al,3)),g); add(('enemies8@-10',side,min(en,4)),g)
            add(('seen@-10',side,len(ch[v]['seenBy'][j])>0),g)
            hp=ch[v]['hp'][j]/ch[v]['maxHp'][j]; add(('hp@-10',side,'>=.9' if hp>=.9 else ('>=.5' if hp>=.5 else '<.5')),g)
        da=min((max(abs(a-x),abs(b-y)) for a,b in altars),default=99)
        add(('altar_d',side,'0-2' if da<=2 else ('3-8' if da<=8 else ('9-16' if da<=16 else '17+'))),g)
        add(('bag',side,'50-149' if g<150 else ('150-299' if g<300 else '300+')),g)
        add(('since_tribute',side,'none' if v not in lastend else ('<100' if e['r']-lastend[v]<100 else ('<250' if e['r']-lastend[v]<250 else '250+'))),g)
        add(('round',side,'<300' if e['r']<300 else ('<600' if e['r']<600 else '600+')),g)
        add(('chan',side,ch[v]['chan'][max(0,i-1)]),g)
print('games',games,'with prism',gp)
for s in 'WL': print('mean carried bag (alive rounds) prism',s,'%.1f'%(sum(bagtime[s])/len(bagtime[s])))
for k in sorted(C,key=lambda k:(k[0],k[1],str(k[2:]))):
    n,g=C[k]; print(k,n,g,'gems/game %.1f'%(g/games))
