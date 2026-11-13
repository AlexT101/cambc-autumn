import json,gzip,glob,collections
B=collections.defaultdict(lambda:[0,0]); first=collections.Counter()
for f in glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json'):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: continue
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    P=[c for c in o['champions'] if names[c['id']]=='Prism']
    if len(P)!=2: continue
    a,b=P; T=len(a['x']); w=m['result']['winner']
    for R in (100,200,300,400):
        if R>=T or not(a['alive'][R] and b['alive'][R]): continue
        pa=a['foc'][R]*a['maxHp'][R] if isinstance(a['maxHp'],list) else a['foc'][R]
        pb=b['foc'][R]*b['maxHp'][R] if isinstance(b['maxHp'],list) else b['foc'][R]
        pr=pa/pb; s=a if pr>=1 else b; pr=max(pr,1/pr)
        k=(R,'<1.1' if pr<1.1 else '<1.3' if pr<1.3 else '<1.6' if pr<1.6 else '1.6+')
        B[k][0]+=1; B[k][1]+= (s['team']==w)
    # first prism death
    for r in range(1,T):
        da=a['alive'][r-1] and not a['alive'][r]; db=b['alive'][r-1] and not b['alive'][r]
        if da or db:
            v=a if da else b; first[('first_prism_death_team_wins', v['team']==w)]+=1; first['r_bucket_%d'%(r//200*200)]+=1; break
    else: first['no_prism_death']+=1
for k in sorted(B): print(k, B[k][0], round(B[k][1]/B[k][0],3))
print(first)
