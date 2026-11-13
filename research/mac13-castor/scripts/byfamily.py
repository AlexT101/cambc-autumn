import json,sys,collections,re,math
W=collections.Counter(); N=collections.Counter()
for b in sys.argv[1:]:
    res=json.load(open(b+'/results.json'))
    for m in res['matches']:
        if m.get('winner') is None: continue
        fam=re.sub(r'-\d+\.map26a$','',m['map'].split('/')[-1])
        cand=m['order'].index(0)
        N[fam]+=1; W[fam]+= (m['winner']==0)
        N['ALL']+=1; W['ALL']+=(m['winner']==0)
for f in sorted(N,key=lambda f:-N[f]):
    p=W[f]/N[f]; print('%-28s %5d %5.1f +-%.1f'%(f,N[f],100*p,196*math.sqrt(p*(1-p)/N[f])))
