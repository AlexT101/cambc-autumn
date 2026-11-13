import json,gzip,collections,sys
A='/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
idx=json.load(open(A+'index.json'))['games']
C=collections.defaultdict(lambda:[0,0])  # key -> [count, gems]
def add(k,g): C[k][0]+=1; C[k][1]+=g
games=0
for d in sorted({r["dir"] for r in idx}):
    r=None
    m=json.load(open(A+d+'/meta.json')); w=m['result']['winner']
    team={c['id']:c['team'] for c in m['champions']}; typ={c['id']:c['name'] for c in m['champions']}
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); rounds=R['round']; ri={x:i for i,x in enumerate(rounds)}
    ch={int(c['id']):c for c in R['champions']}
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    spawn={}
    for c in m['champions']:
        cc=ch[c['id']]; spawn[c['id']]=(cc['x'][0],cc['y'][0])
    tspawn={t:[spawn[i] for i in spawn if team[i]==t] for t in (0,1)}
    games+=1
    for e in ev:
        if e['k']!='death' or e.get('by') is None: continue
        v=e['v']; g=e.get('gemsTo',0) or 0
        if v not in team: continue
        side='W' if team[v]==w else 'L'
        add(('all',side),g)
        if g<50: continue
        if typ[v]=='Prism': add(('prism',side),g)
        i=ri.get(e['r']); 
        if i is None: continue
        x,y=e['at']
        def cnt(t,rad,j):
            n=0
            for o,c in ch.items():
                if team.get(o)!=t or o==v or not c['alive'][j] or c['x'][j] is None: continue
                if max(abs(c['x'][j]-x),abs(c['y'][j]-y))<=rad: n+=1
            return n
        j5=max(0,i-5)
        al=cnt(team[v],6,j5); en=cnt(1-team[v],6,j5)
        ds_own=min(max(abs(a-x),abs(b-y)) for a,b in tspawn[team[v]]); ds_en=min(max(abs(a-x),abs(b-y)) for a,b in tspawn[1-team[v]])
        zone='own' if ds_own*2<ds_en else ('enemy' if ds_en*2<ds_own else 'mid')
        c=ch[v]; chan=c['chan'][max(0,i-1)]
        hp5=c['hp'][j5]; mx=c['maxHp'][j5]
        seen5=len(c['seenBy'][j5])>0
        add(('big',side),g)
        add(('type',side,typ[v]),g)
        add(('zone',side,zone),g)
        add(('odds5',side,'%d v %d'%(al+1,en)),g)
        add(('chan',side,chan),g)
        add(('hp5',side,'full' if hp5>=0.9*mx else ('half+' if hp5>=0.5*mx else 'low')),g)
        add(('seen5',side,seen5),g)
        add(('bag',side,'50-99' if g<100 else ('100-199' if g<200 else '200+')),g)
        add(('cause',side,e.get('cause')),g)
print('games',games)
for k in sorted(C,key=lambda k:(k[0],str(k[1:]))):
    n,g=C[k]; print(k, n, g, 'gems/game %.1f'%(g/games))
