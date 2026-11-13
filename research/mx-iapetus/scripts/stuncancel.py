import json,gzip,collections
A='/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
idx=json.load(open(A+'index.json'))['games']; seen={r['dir']:r for r in idx}
TYPES=json.load(open(A+'enums.json')).get('championTypes') or None
stunner=collections.Counter(); allyd=collections.Counter(); lost_turns=[]; enemy_near_start=collections.Counter()
games=0; per_game=[]
for d,r in list(seen.items()):
    m=json.load(open(A+d+'/meta.json')); team={c['id']:c['team'] for c in m['champions']}; typ={c['id']:c['name'] if 'name' in c else c['type'] for c in m['champions']}
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); rounds=R['round']
    pos={c['id']:(c['x'],c['y'],c['alive']) for c in R['champions']}
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    w=r['winner']; games+=1; start={}; lost=0
    laststun={}
    for e in ev:
        if e['k'] in ('cast','attack') and e.get('stun'):
            for v in e['stun']: laststun[v]=(e['a'],e['r'])
        if e['k']=='tribute_start' and e.get('gems',0)>=100:
            start[e['a']]=(e['r'],e['dur'])
            i=rounds.index(e['r']) if e['r'] in rounds else None
            if i is not None and team[e['a']]==w:
                px,py,_=pos[e['a']][0][i],pos[e['a']][1][i],0
                if px is None: continue
                dmin=min((max(abs(pos[o][0][i]-px),abs(pos[o][1][i]-py)) for o in pos if team[o]!=team[e['a']] and pos[o][2][i] and pos[o][0][i] is not None), default=99)
                enemy_near_start[min(dmin//4,5)]+=1
        if e['k']=='tribute_cancel' and e.get('gems',0)>=100 and team.get(e['a'])==w:
            s=start.get(e['a']); 
            if s: lost+= s[1]-e.get('left',0)
            if e.get('cause')=='stun' and e['a'] in laststun:
                st,rr=laststun[e['a']]; stunner[typ[st]]+=1
                i=rounds.index(rr) if rr in rounds else None
                if i is not None:
                    px,py=pos[e['a']][0][i],pos[e['a']][1][i]
                    if px is None: continue
                    da=min((max(abs(pos[o][0][i]-px),abs(pos[o][1][i]-py)) for o in pos if o!=e['a'] and team[o]==w and pos[o][2][i] and pos[o][0][i] is not None), default=99)
                    allyd[min(da,12)]+=1
    per_game.append(lost)
print('games',games,'mean channel turns lost to cancels (winner, 100+ bags) per game %.1f'%(sum(per_game)/games))
print('stunner types',stunner.most_common())
print('nearest ally distance at stun',sorted(allyd.items()))
print('nearest enemy at big-tribute start (bucket of 4 tiles)',sorted(enemy_near_start.items()))
