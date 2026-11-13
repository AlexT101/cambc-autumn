import json,gzip,glob,collections
dirs=[d.rsplit('/',1)[0] for d in glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')]
agg=collections.defaultdict(list)
for d in dirs:
    m=json.load(open(d+'/meta.json'))
    if 'bel-study512' not in m['source']: continue
    w=m['result']['winner']
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz')]
    shops=collections.defaultdict(list)
    for e in ev:
        if e['k']=='shop': shops[e['a']].append(e['r'])
    for c in o['champions']:
        nm=names[c['id']]
        if nm not in ('Prism','Vesper Vale','Vendetta'): continue
        res='W' if c['team']==w else 'L'
        T=len(c['gold'])
        visits=sorted(set(shops[c['id']]))
        # gold buckets by phase
        for lo,hi in ((0,300),(300,600),(600,1000),(1000,2000)):
            seg=c['gold'][lo:min(hi,T)]
            if seg: agg[(nm,res,lo,'gold')].append(sum(seg)/len(seg))
            gs=c['gems'][lo:min(hi,T)]
            if gs: agg[(nm,res,lo,'gems')].append(sum(gs)/len(gs))
        agg[(nm,res,'shopvisits')].append(len(visits))
        agg[(nm,res,'deaths')].append(c['deaths'][-1])
        agg[(nm,res,'rounds')].append(T)
for k in sorted(agg,key=str):
    v=agg[k]; print(k, len(v), round(sum(v)/len(v),1))
