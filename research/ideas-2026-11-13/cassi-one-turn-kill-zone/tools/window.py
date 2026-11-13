import json,gzip,os,collections,statistics as st
rows=json.load(open('../rows-r8-all.json'))
D=json.load(open('/home/ubuntu/tmp-offload/cassizone/deaths2.json'))
cheb=lambda a,b: 99 if None in a or None in b else max(abs(a[0]-b[0]),abs(a[1]-b[1]))
A=collections.Counter(); n=0; allies_near=[]; enemies_near=[]; fight=0; cassi_dmg=[]; dd_after=[]
for x in D:
    if x['body']!='Cassi': continue
    d=x['game']; m=json.load(open(d+'/meta.json')); P=m['draft']['picks']; r=rows[os.path.basename(m['source']).split('.')[0]]
    us=[t for t in (0,1) if sorted(P[t])==sorted(r['our_picks']) and sorted(P[1-t])==sorted(r['opp_picks'])][0]
    ours={c['name']:c['id'] for c in m['champions'] if c['team']==us}; fish={c['name']:c['id'] for c in m['champions'] if c['team']!=us}
    cid=ours['Cassi']; vid=fish['Vesper Vale']
    R=json.load(gzip.open(d+'/rounds.json.gz','rt')); idx={v:i for i,v in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    ca=C[cid]; ve=C[vid]
    evs=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    r0=x['r']
    # window: last 6 rounds before death round
    moves=[e for e in evs if e.get('a')==cid and e['k']=='move' and r0-6<=e['r']<r0]
    for e in moves:
        j=idx[e['r']]-1  # Vesper at previous round end
        pv=(ve['x'][j],ve['y'][j])
        A['toward' if cheb(e['to'],pv)<cheb(e['f'],pv) else ('away' if cheb(e['to'],pv)>cheb(e['f'],pv) else 'level')]+=1
    # Cassi damage dealt to Fish champions in last 6 rounds
    dealt=0
    for e in evs:
        if e.get('a')==cid and r0-6<=e['r']<=r0 and isinstance(e.get('dmg'),list):
            dealt+=sum(v for t,v in e['dmg'])
    cassi_dmg.append(dealt)
    j=idx[r0]-2
    pc=(ca['x'][j],ca['y'][j])
    an=sum(1 for c in R['champions'] if c['team']==us and c['id']!=cid and c['alive'][j] and cheb(pc,(c['x'][j],c['y'][j]))<=4)
    en=sum(1 for c in R['champions'] if c['team']!=us and c['alive'][j] and cheb(pc,(c['x'][j],c['y'][j]))<=8)
    allies_near.append(an); enemies_near.append(en)
print('Cassi moves in the 6 rounds before death, relative to Vesper:', dict(A))
print('allies within 4 of Cassi 2 rounds before:', sorted(collections.Counter(allies_near).items()))
print('Fish champions within 8 of Cassi 2 rounds before:', sorted(collections.Counter(enemies_near).items()))
print('Cassi champion damage dealt in last 6 rounds: median', st.median(cassi_dmg), 'zero in', sum(v==0 for v in cassi_dmg), 'of', len(cassi_dmg))
