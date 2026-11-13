# Winning enemy tributes and how CAND stopped them: per game, the enemy's winning channels, how each ended
# (landed / stun / lock / manual), our deaths within W rounds after the stop near the altar (lives, gems),
# channeller kills by us within W rounds (gems taken), and restarts. Optional D trace: E-class deaths (deaths.py).
# Usage: stops.py EXTRACT_DIR CAND_NAME [W]
import json,gzip,sys,collections
A=sys.argv[1].rstrip('/')+'/'; cand=sys.argv[2]; W=int(sys.argv[3]) if len(sys.argv)>3 else 12
idx=json.load(open(A+'index.json'))['games']
c=collections.Counter(); games=0; wins=0
for r in idx:
    if cand not in r['teams'] or not r.get('ok',True): continue
    ct=r['teams'].index(cand); games+=1; wins+=r['winner']==ct
    d=r['dir']; m=json.load(open(A+d+'/meta.json')); team={c_['id']:c_['team'] for c_ in m['champions']}
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    total=[0,0]; open_={}  # channeller -> (round, altar, gems)
    stops=[]  # (round, channeller, altar, cause, gems)
    for e in ev:
        k=e['k']
        if k=='tribute_end':
            t=team[e['a']]; total[t]=e.get('total',total[t]+e['gems'])
            if e['a'] in open_ and t!=ct: c['landed']+=1
            open_.pop(e['a'],None)
        elif k=='tribute_start':
            t=team[e['a']]
            if t!=ct and total[t]+e['gems']>=1000:
                open_[e['a']]=(e['r'],tuple(e['altar']),e['gems']); c['win_starts']+=1
        elif k=='tribute_cancel' and e['a'] in open_:
            s=open_.pop(e['a']); c['cancel_'+e.get('cause','?')]+=1
            stops.append((e['r'],e['a'],s[1],e.get('cause','?'),s[2]))
    # after each stop: our deaths near the altar, channeller deaths by us
    deaths=[e for e in ev if e['k']=='death' and e.get('linked') is None]
    for (rr,ch,alt,cause,g) in stops:
        for e in deaths:
            if not (rr-1<=e['r']<=rr+W): continue
            v=e['v']; gems=e.get('gems',0)+sum(x.get('gems',0) for x in ev if x['k']=='death' and x.get('linked')==v and x['r']==e['r'])
            if team[v]==ct and max(abs(e['at'][0]-alt[0]),abs(e['at'][1]-alt[1]))<=7:
                c['our_dead_'+cause]+=1; c['our_dead_gems']+=gems; c['our_dead']+=1
            if v==ch and e.get('by') in team and team[e['by']]==ct:
                c['ch_killed_'+cause]+=1; c['ch_killed_gems']+=gems; c['ch_killed']+=1
print(f'games {games} win {100*wins/max(1,games):.1f}%  (per game; W={W})')
for k in sorted(c): print(f'  {k:22} {c[k]/games:7.3f}  n={c[k]}')
