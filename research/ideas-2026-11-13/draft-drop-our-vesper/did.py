import json, collections, math
G='/home/ubuntu/cambc-autumn/research/ladder-scrims-2026-11-06/data/games.jsonl'
gs=[json.loads(l) for l in open(G)]
gs=[g for g in gs if g.get('status')=='finished' and g.get('our_picks') and g.get('result') in ('win','loss') and g['version']>=113]
def tgt(g,which):
    if which=='fish8': return g['opp_name']=='Intercontinental Fish' and g.get('refset')=='r8'
    if which=='mite': return g['opp_name']=='Mite'
    if which=='mitev': return g['opp_name']=='Mite' and 'Vesper Vale' in g['opp_picks']
def other(g): return g['opp_name'] not in ('Mite','Intercontinental Fish')
for which in ('fish8','mite','mitev'):
    # cell = (version, map, side); our picks fixed per cell
    T=collections.defaultdict(list); O=collections.defaultdict(list); V={}
    for g in gs:
        c=(g['version'],g['map'],g['side'])
        V[c]='Vesper Vale' in g['our_picks']
        if tgt(g,which): T[c].append(g['result']=='win')
        elif other(g): O[c].append(g['result']=='win')
    d={True:[],False:[]}
    for c in T:
        if c in O and O[c]:
            t=sum(T[c])/len(T[c]); o=sum(O[c])/len(O[c])
            d[V[c]].append((t-o,len(T[c])))
    res={}
    for k in (True,False):
        xs=[x for x,_ in d[k]]; n=len(xs); m=sum(xs)/n; sd=math.sqrt(sum((x-m)**2 for x in xs)/(n-1))
        res[k]=(m,sd/math.sqrt(n),n)
        print(which,'ourV' if k else 'noV',f'cells {n}: target - others = {100*m:+.1f} +-{100*sd/math.sqrt(n):.1f}')
    dd=res[True][0]-res[False][0]; se=math.hypot(res[True][1],res[False][1])
    print(which,f'  DiD ourV - noV = {100*dd:+.1f} +-{100*se:.1f} (z {dd/se:.2f})')
