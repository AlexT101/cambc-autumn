import json,gzip,collections,statistics as S
A='/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
idx=json.load(open(A+'index.json'))['games']; seen={r['dir']:r for r in idx}
rows=[]
for d,r in seen.items():
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); rounds=R['round']; n=len(rounds)
    m=json.load(open(A+d+'/meta.json')); team={c['id']:c['team'] for c in m['champions']}; typ={c['id']:c['name'] for c in m['champions']}
    w=r['winner']; wealth=[R['gems'][w][i]+sum(c['gems'][i] for c in R['champions'] if c['team']==w) for i in range(n)]
    r1k=next((rounds[i] for i in range(n) if wealth[i]>=1000),None)
    if r1k is None: continue
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    # last tribute_start by winner that completed (tribute_end) -> the winning one
    last_start=None; first_big=None; chan_lost=0; open_={}
    for e in ev:
        if e['k']=='tribute_start' and team.get(e['a'])==w:
            open_[e['a']]=e
            if e['r']>=r1k-20 and e.get('gems',0)>=100 and first_big is None: first_big=e['r']
        if e['k']=='tribute_end' and team.get(e['a'])==w and e['a'] in open_: last_start=open_[e['a']]
        if e['k']=='tribute_cancel' and team.get(e['a'])==w and e['a'] in open_ and e['r']>=r1k-20:
            s=open_[e['a']]; chan_lost+= e['r']-s['r']
    end=rounds[-1]
    ws=last_start['r'] if last_start else None
    rows.append((end-r1k, (first_big-r1k) if first_big else None, (ws-r1k) if ws else None, (end-ws) if ws else None, chan_lost, typ.get(last_start['a']) if last_start else None, last_start.get('gems') if last_start else None))
lag=[x[0] for x in rows]; print('n',len(rows),'lag median',S.median(lag))
for q in (0.5,0.75,0.9):
    k=int(q*len(rows)); srt=sorted(rows,key=lambda x:x[0]); x=srt[k]; print(q, x)
print('R1000 -> first big start median', S.median([x[1] for x in rows if x[1] is not None]))
print('R1000 -> winning start median', S.median([x[2] for x in rows if x[2] is not None]), 'p75', sorted([x[2] for x in rows if x[2] is not None])[3*len(rows)//4])
print('winning channel length median', S.median([x[3] for x in rows if x[3] is not None]))
print('rounds in cancelled channels after R1000-20 mean %.1f median %s'%(S.mean([x[4] for x in rows]), S.median([x[4] for x in rows])))
print('winning tributer', collections.Counter(x[5] for x in rows).most_common(6))
print('winning bag median', S.median([x[6] for x in rows if x[6]]))
