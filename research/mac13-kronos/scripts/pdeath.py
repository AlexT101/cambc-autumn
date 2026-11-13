import json,gzip,glob,collections
K=collections.Counter(); A=collections.Counter(); G=[]
for f in glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json'):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: continue
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k']!='death' or names.get(e['v'])!='Prism': continue
        by=e.get('by'); K[names.get(by,'camp/none') if by is not None else 'camp/none']+=1
        A[len(e.get('assists',[]))]+=1; G.append(e['gems'])
print(K); print('assists',A); G.sort(); n=len(G); print('gems',[G[int(n*q)] for q in (.1,.25,.5,.75,.9)])
