import json,gzip,glob,collections
st=collections.Counter()
for f in glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json'):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: continue
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    P=[c for c in o['champions'] if names[c['id']]=='Prism']
    if len(P)!=2: continue
    a,b=P; T=len(a['x']); w=m['result']['winner']
    for r in range(T):
        if a['alive'][r] and b['alive'][r] and max(a['foc'][r]/b['foc'][r], b['foc'][r]/a['foc'][r])>=2:
            s,v=(a,b) if a['foc'][r]>b['foc'][r] else (b,a)
            won = s['team']==w
            sd = any(not s['alive'][q] for q in range(r,T)); vd=any(not v['alive'][q] for q in range(r,T))
            st[(won,'strong_dies_later' if sd else '-', 'weak_dies_later' if vd else '-')]+=1
            st[(won,'r<300' if r<300 else 'r<600' if r<600 else 'r600+')]+=1
            st[(won,'gems_at_r_strong_bucket', min(s['gems'][r]//50*50,300))]+=1
            break
for k in sorted(st,key=str): print(k, st[k])
