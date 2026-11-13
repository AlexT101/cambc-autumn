import json,gzip,collections,statistics as S
A='/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
idx=json.load(open(A+'index.json'))['games']; seen={r['dir']:r for r in idx}
out=collections.Counter(); firstloss=[]
for d,r in seen.items():
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); rounds=R['round']; n=len(rounds)
    m=json.load(open(A+d+'/meta.json')); team={c['id']:c['team'] for c in m['champions']}; typ={c['id']:c['name'] for c in m['champions']}
    W=[[R['gems'][t][i]+sum(c['gems'][i] for c in R['champions'] if c['team']==t) for i in range(n)] for t in (0,1)]
    r1k=[next((rounds[i] for i in range(n) if W[t][i]>=1000),None) for t in (0,1)]
    if None in r1k: continue
    f=0 if r1k[0]<=r1k[1] else 1; w=r['winner']
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    canc=[0,0]; starts=[0,0]; deaths=[collections.Counter(),collections.Counter()]; open_={}
    for e in ev:
        if e['r']<min(r1k)-10: continue
        if e['k']=='tribute_start' and e.get('gems',0)>=100: open_[e['a']]=e; starts[team[e['a']]]+=1
        if e['k']=='tribute_cancel' and e['a'] in open_: canc[team[e['a']]]+=e['r']-open_[e['a']]['r']
        if e['k']=='death' and e['v'] in team and e.get('gems',0)>=100: deaths[team[e['v']]][typ[e['v']]]+=1
    key='first won' if f==w else 'first lost'
    out[key]+=1
    if f!=w: firstloss.append((r1k[1-f]-r1k[f], canc[f], starts[f], dict(deaths[f]), canc[1-f], rounds[-1]-r1k[f]))
print(out)
print('first-lost cases: gap, first canc rounds, first big starts, first big-bag deaths, second canc, first lag')
for x in sorted(firstloss,key=lambda x:x[0])[::4]: print(x)
print('first-lost: big-bag death of first team in', sum(1 for x in firstloss if x[3]), 'of', len(firstloss))
print('median first canc rounds', S.median([x[1] for x in firstloss]), 'median second canc', S.median([x[4] for x in firstloss]))
