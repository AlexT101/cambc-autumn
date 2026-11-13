import json,gzip,glob,collections
st=collections.Counter(); waits=[]; dists=[]
for f in glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json'):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: continue
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    P=[c for c in o['champions'] if names[c['id']]=='Prism']
    if len(P)!=2: continue
    a,b=P; T=len(a['x']); w=m['result']['winner']
    # first round where focus ratio >= 2 with both alive
    for r in range(T):
        if a['alive'][r] and b['alive'][r] and max(a['foc'][r]/b['foc'][r], b['foc'][r]/a['foc'][r])>=2:
            s,v=(a,b) if a['foc'][r]>b['foc'][r] else (b,a)
            st['dominant_episode']+=1; st['dom_team_wins']+= s['team']==w
            # what happens next: weak prism dies / ratio falls <1.5 / game end
            res='end'
            for q in range(r,T):
                if not v['alive'][q]: res='weak_died'; waits.append(q-r); break
                if not s['alive'][q]: res='strong_died'; break
                if s['foc'][q]/max(1,v['foc'][q])<1.5: res='recovered'; break
            st[res]+=1
            # mean distance between prisms during next 100 rounds
            ds=[max(abs(a['x'][q]-b['x'][q]),abs(a['y'][q]-b['y'][q])) for q in range(r,min(T,r+100)) if a['alive'][q] and b['alive'][q]]
            if ds: dists.append(sum(ds)/len(ds))
            st['round_sum']+=r
            break
print(st); waits.sort(); n=len(waits); print('rounds to weak death',[waits[int(n*q)] for q in (.1,.25,.5,.75,.9)])
dists.sort(); n=len(dists); print('mean dist next 100',[round(dists[int(n*q)],1) for q in (.1,.25,.5,.75,.9)])
