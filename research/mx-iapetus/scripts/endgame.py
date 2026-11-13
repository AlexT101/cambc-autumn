import json,gzip,collections,sys
A='/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
idx=json.load(open(A+'index.json'))['games']
seen={r['dir']:r for r in idx}
stats=collections.Counter(); lags=[]; both=[]; cancels=collections.Counter(); starts=[]
for d,r in seen.items():
    try:
        R=json.load(gzip.open(A+d+'/rounds.json.gz'))
    except Exception: continue
    rounds=R['round']; n=len(rounds)
    wealth=[[0]*n,[0]*n]
    for t in (0,1):
        for i in range(n): wealth[t][i]=R['gems'][t][i]
    for c in R['champions']:
        for i in range(n): wealth[c['team']][i]+=c['gems'][i]
    r1k=[next((rounds[i] for i in range(n) if wealth[t][i]>=1000),None) for t in (0,1)]
    w=r['winner']; end=rounds[-1]
    if r1k[w] is None: stats['winner never 1000 wealth']+=1; continue
    lags.append(end-r1k[w])
    if r1k[1-w] is not None:
        first=0 if (r1k[0]<=r1k[1]) else 1
        both.append((first==w, r1k[1-w]-r1k[w], end-r1k[w]))
    else: stats['only winner reached']+=1
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    team={c['id']:c['team'] for c in json.load(open(A+d+'/meta.json'))['champions']}
    for e in ev:
        if e['k']=='tribute_cancel' and e.get('gems',0)>=100:
            cancels[(e['a'] in team and team[e['a']]==w, e.get('cause'))]+=1
        if e['k']=='tribute_start' and e.get('gems',0)>=300:
            starts.append(e['r'])
import statistics as S
print('games',len(seen), dict(stats))
lags.sort(); print('winner R1000->end lag median',S.median(lags),'p75',lags[3*len(lags)//4],'p90',lags[9*len(lags)//10])
print('both reached',len(both),'first won',sum(1 for b in both if b[0]))
gaps=sorted(abs(b[1]) for b in both); print('gap between R1000s median',S.median(gaps))
print('big tribute cancels (winner?,cause):',cancels.most_common(12))
