import json,gzip,glob,sys,collections
dirs=[d.rsplit('/',1)[0] for d in glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')]
S=collections.defaultdict(lambda: collections.defaultdict(float)); n=collections.Counter()
for d in dirs:
    m=json.load(open(d+'/meta.json'))
    if 'bel-study512' not in m['source']: continue
    w=m['result']['winner']; R=m['result']['rounds']
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    names={c['id']:c['name'] for c in m['champions']}
    for c in o['champions']:
        res='W' if c['team']==w else 'L'
        nm=names[c['id']]
        g=c['gold']; al=c['alive']
        k=(res,nm); n[k]+=1
        T=len(g)
        S[k]['avg_gold']+=sum(g)/T
        S[k]['rounds_ge30']+=sum(1 for x in g if x>=30)/T
        S[k]['rounds_ge60']+=sum(1 for x in g if x>=60)/T
        S[k]['earned']+=c['earned'][-1]
        S[k]['end_gold']+=g[-1]
        # gold at death
        S[k]['gold_lost_at_death']+=0
        S[k]['r300_gold']+=g[min(299,T-1)]
        S[k]['r300_earned']+=c['earned'][min(299,T-1)]
for k in sorted(n):
    print(k, n[k], {a:round(v/n[k],2) for a,v in S[k].items()})
