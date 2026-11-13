import json,gzip,collections
A='/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/'
idx=json.load(open(A+'index.json'))['games']
tab=collections.defaultdict(collections.Counter); cover=collections.defaultdict(list)
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
for d in sorted({r["dir"] for r in idx}):
    m=json.load(open(A+d+'/meta.json')); w=m['result']['winner']
    team={c['id']:c['team'] for c in m['champions']}
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); rounds=R['round']; ri={x:i for i,x in enumerate(rounds)}
    ch={int(c['id']):c for c in R['champions']}; W=R['wards']
    ev=[json.loads(l) for l in gzip.open(A+d+'/events.jsonl.gz','rt')]
    altars=sorted(set(tuple(e['altar']) for e in ev if e['k']=='tribute_start'))
    n=len(rounds)
    # altar coverage by each team's wards over the last 150 rounds
    for t in (0,1):
        s=0;k=0
        for i in range(max(0,n-150),n):
            ws=[(x[2],x[3]) for x in W[i] if x[1]==t]
            s+=sum(1 for a in altars if any(cheb(a,p)<=6 for p in ws)); k+=1
        if altars and k: cover['W' if t==w else 'L'].append(s/k/len(altars))
    open_={}
    for e in ev:
        if e['k']=='tribute_start' and e.get('gems',0)>=100:
            i=ri.get(e['r']); 
            if i is None: continue
            t=team[e['a']]; p=tuple(e['at'])
            ew=any(x[1]!=t and cheb((x[2],x[3]),p)<=6 for x in W[i])
            ec=any(team.get(o)!=t and c['alive'][i] and c['x'][i] is not None and cheb((c['x'][i],c['y'][i]),p)<=8 for o,c in ch.items())
            open_[e['a']]=('W' if t==w else 'L', 'enemy ward' if ew else 'no ward', 'enemy body<=8' if ec else 'no body')
        elif e['k'] in ('tribute_end','tribute_cancel') and e['a'] in open_:
            k=open_.pop(e['a']); out='done' if e['k']=='tribute_end' else e.get('cause')
            tab[k][out]+=1; tab[k[:2]][out]+=1
for s in 'WL': print('share of altars covered by own wards, last 150 rounds',s,'%.3f'%(sum(cover[s])/len(cover[s])))
for k in sorted(tab):
    c=tab[k]; t=sum(c.values()); print(k,t,'done %.3f'%(c['done']/t),dict(c))
