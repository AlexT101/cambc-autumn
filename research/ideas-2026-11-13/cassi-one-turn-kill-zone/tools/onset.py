import json,gzip,os,collections,statistics as st
rows=json.load(open('../rows-r8-all.json'))
D=json.load(open('/home/ubuntu/tmp-offload/cassizone/deaths2.json'))
cheb=lambda a,b: 99 if None in a or None in b else max(abs(a[0]-b[0]),abs(a[1]-b[1]))
onset=[]; firstseen=[]; hitfirst=[]; rcrate=[0,0]
def dmgs(e):
    v=e.get('dmg')
    if v is None: return []
    if isinstance(v,(int,float)): return [(e.get('tgt'),v)]
    return [(t,a) for t,a in v]
for x in D:
    if x['body']!='Cassi': continue
    d=x['game']; m=json.load(open(d+'/meta.json')); P=m['draft']['picks']; r=rows[os.path.basename(m['source']).split('.')[0]]
    us=[t for t in (0,1) if sorted(P[t])==sorted(r['our_picks']) and sorted(P[1-t])==sorted(r['opp_picks'])][0]
    ours={c['name']:c['id'] for c in m['champions'] if c['team']==us}; fish={c['name']:c['id'] for c in m['champions'] if c['team']!=us}
    cid=ours['Cassi']; vid=fish['Vesper Vale']
    R=json.load(gzip.open(d+'/rounds.json.gz','rt')); idx={v:i for i,v in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    ca=C[cid]; ve=C[vid]
    evs=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    rs=set(e['r'] for e in evs if e.get('a')==cid and e['k']=='recall_start')
    dmg=collections.defaultdict(float)
    for e in evs:
        for t,v in dmgs(e):
            if t==cid: dmg[e['r']]+=v
    for j,rr in enumerate(R['round']):
        if rr>=300 and ca['alive'][j]: rcrate[0]+=1; rcrate[1]+= rr in rs
    r0=x['r']; t=r0
    while (t-1 in rs) or (t-2 in rs): t-= 1 if (t-1 in rs) else 2
    j=idx[t]; dd=cheb((ca['x'][j],ca['y'][j]),(ve['x'][j],ve['y'][j]))
    onset.append((r0-t, dd, ca['hp'][j]/ca['maxHp'][j], vid in (ca['sees'][j] or []), dmg.get(t,0)>0 or dmg.get(t-1,0)>0))
    fd=[rr for rr in range(r0-15,r0+1) if dmg.get(rr,0)>0]
    hitfirst.append(r0-fd[0] if fd else -1)
    s=None
    for rr in range(r0-1,r0-16,-1):
        jj=idx.get(rr)
        if jj is None or vid not in (ca['sees'][jj] or []): break
        s=rr
    firstseen.append((r0-s, cheb((ca['x'][idx[s]],ca['y'][idx[s]]),(ve['x'][idx[s]],ve['y'][idx[s]]))) if s else None)
print('Cassi late recall_start rate (rounds with a start / alive rounds):', rcrate[1], rcrate[0], f'{rcrate[1]/rcrate[0]*100:.1f}%')
print('retreat streak length before death (rounds) median', st.median(o[0] for o in onset), 'dist at onset median', st.median(o[1] for o in onset))
print('onset dist hist', sorted(collections.Counter(min(o[1],12) for o in onset).items()))
print('streak len hist', sorted(collections.Counter(min(o[0],20) for o in onset).items()))
print('onset: hp/max med', st.median(o[2] for o in onset), 'sees her at onset', sum(o[3] for o in onset), 'damaged at/just before onset', sum(o[4] for o in onset), 'of', len(onset))
print('rounds from first damage (within 15) to death:', sorted(collections.Counter(hitfirst).items()))
fs=[f for f in firstseen if f]
print('Cassi saw her continuously to death: n', len(fs), 'of', len(firstseen), '; rounds med', st.median(f[0] for f in fs), 'dist at first continuous sight med', st.median(f[1] for f in fs), sorted(collections.Counter(min(f[1],12) for f in fs).items()))
