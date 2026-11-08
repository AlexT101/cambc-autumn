import pickle,collections,sys
rows=pickle.load(open('/home/ubuntu/tmp-offload/emblem/live_items.pkl','rb'))
seen=set();R=[]
for r in rows:
    k=(r['dir'],r['id'])
    if k in seen: continue
    seen.add(k);R.append(r)
OPP={'I':'F','M':'M'}
CPS=[int(x) for x in sys.argv[1].split(',')]; WHO=sys.argv[2].split(',') if len(sys.argv)>2 else ['F','us-F','M','us-M']
VERS=set(int(v) for v in sys.argv[3].split(',')) if len(sys.argv)>3 else None
for CPR in CPS:
  print('==== r',CPR)
  agg=collections.defaultdict(collections.Counter);n=collections.Counter()
  for r in R:
    if CPR not in r['cp'] or (VERS and r['ver'] not in VERS): continue
    o=OPP[r['opp']]; who='us-'+o if r['ours'] else o
    key=(r['name'],who);n[key]+=1
    c=r['cp'][CPR]
    for (fam,st),k in c['emb'].items(): agg[key][fam]+=k
    agg[key]['_shards']+=c['shards'];agg[key]['_gold']+=c['gold'];agg[key]['_earned']+=c['earned'];agg[key]['_win']+=r['team_win']
  for name in ['Vesper Vale','Vendetta','Heart of Ruin','Marcella','Cassi','Issac','Prism','Tavi','Willow','Ren','Varg','Stellar','Ryth']:
    for who in WHO:
      key=(name,who)
      if n[key]<15: continue
      a=agg[key];N=n[key]
      fams=' '.join(f'{f[:4]}{a[f]/N:.2f}' for f,_ in sorted(((f,v) for f,v in a.items() if not f.startswith('_')),key=lambda x:-x[1]) if a[f]/N>=0.05)
      print(f'{name[:8]:8s} {who:4s} n={N:4d} win={a["_win"]/N:.2f} earn={a["_earned"]/N:6.0f} gold={a["_gold"]/N:4.0f} sh={a["_shards"]/N:5.1f} | {fams}')
