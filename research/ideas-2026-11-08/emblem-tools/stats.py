import pickle,collections,sys
rows=pickle.load(open('/home/ubuntu/tmp-offload/emblem/live_items.pkl','rb'))
seen=set();R=[]
for r in rows:
    k=(r['dir'],r['id'])
    if k in seen: continue
    seen.add(k);R.append(r)
OPP={'I':'F','M':'M'}
CPR=int(sys.argv[1])
agg=collections.defaultdict(lambda: collections.Counter())
for r in R:
    if CPR not in r['cp']: continue
    o=OPP[r['opp']]; who='us-'+o if r['ours'] else o
    c=r['cp'][CPR]; a=agg[(r['name'],who)]; a['n']+=1
    for (fam,st),k in c['emb'].items():
        if fam=='Bruiser':
            for s in range(3): a[s]+=k*(5 if s==st else 1)
        elif fam=='Power': a[st]+=6*k
        elif fam=='Greed': a[st]+=40*k
        else: a[st]+=5*k
    a['tot']+=c['shards']
for name in ['Vesper Vale','Vendetta','Heart of Ruin','Marcella','Prism','Issac','Cassi']:
    for who in ['F','us-F','M','us-M']:
        a=agg[(name,who)]
        if a['n']<15: continue
        s=a[0]+a[1]+a[2]
        print(f'{name[:8]:8s} {who:4s} n={a["n"]:4d} emblem-stat shards/game S {a[0]/a["n"]:5.1f} F {a[1]/a["n"]:5.1f} H {a[2]/a["n"]:5.1f}  H share {a[2]/max(s,1):.2f}')
