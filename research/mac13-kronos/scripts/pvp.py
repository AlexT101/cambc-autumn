import json,gzip,glob,collections
# Prism-vs-Prism encounters: first round of an episode where both alive Prisms within 6 (Chebyshev).
rows=[]
for f in glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json'):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: continue
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    P=[c for c in o['champions'] if names[c['id']]=='Prism']
    if len(P)!=2: continue
    a,b=P; T=len(a['x']); w=m['result']['winner']
    last=-100
    for r in range(T):
        if not(a['alive'][r] and b['alive'][r]): continue
        dd=max(abs(a['x'][r]-b['x'][r]),abs(a['y'][r]-b['y'][r]))
        if dd<=6:
            if r-last>20:
                # outcome within 20 rounds
                out='none'
                for s in range(r+1,min(T,r+21)):
                    if not a['alive'][s] and a['alive'][s-1]: out='a_died'; break
                    if not b['alive'][s] and b['alive'][s-1]: out='b_died'; break
                fa=a['foc'][r]; fb=b['foc'][r]; ha=a['hp'][r]; hb=b['hp'][r]
                rows.append(dict(r=r,fr=fa/fb,hr=ha/hb, ea=fa*ha, eb=fb*hb, out=out, aw=(a['team']==w)))
            last=r
n=len(rows); print('episodes',n)
c=collections.Counter(x['out'] for x in rows); print(c)
# by power ratio (focus*hp), outcome of the stronger
B=collections.defaultdict(collections.Counter)
for x in rows:
    pr=x['ea']/x['eb']
    s,o=(pr,x['out']) 
    if pr<1: pr=1/pr; o={'a_died':'strong_died','b_died':'weak_died'}.get(x['out'],'none') if True else 0
    else: o={'a_died':'weak_died','b_died':'strong_died'}.get(x['out'],'none')
    # fix mapping: if a stronger (s>=1): a_died->strong_died
    if s>=1: o={'a_died':'strong_died','b_died':'weak_died'}.get(x['out'],'none')
    else: o={'b_died':'strong_died','a_died':'weak_died'}.get(x['out'],'none')
    k=('<1.2' if pr<1.2 else '<1.5' if pr<1.5 else '<2' if pr<2 else '<3' if pr<3 else '3+')
    B[k][o]+=1
for k in ['<1.2','<1.5','<2','<3','3+']: 
    t=sum(B[k].values()); print(k,t,{o:round(v/t,3) for o,v in B[k].items()})
# per game: number of encounter episodes
