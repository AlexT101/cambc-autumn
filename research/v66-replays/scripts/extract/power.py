import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
CK=[100,200,300,400,600,800]
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']
    C={c['id']:c for c in m['champions']}
    out={}
    for rn in CK:
        if rn>len(R['round']): continue
        i=rn-1
        row={}
        for side,t in (('us',us),('them',1-us)):
            cs=[c for c in R['champions'] if c['team']==t]
            row[side]=dict(earned=sum(c['earned'][i] for c in cs), mh=sum(c['maxHp'][i] for c in cs), str=sum(c['str'][i] for c in cs),
               gems=sum(c['gems'][i] for c in cs), trib=R['gems'][t][i], deaths=sum(c['deaths'][i] for c in cs),
               byname={C[c['id']]['name']:(c['maxHp'][i],c['str'][i],c['foc'][i]) for c in cs})
        out[rn]=row
    return dict(opp=r['opp'],won=r['won'],map=r['map'],ck=out)
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,games()))
    json.dump(res,open(sys.argv[1]+'/power.json','w'))
    for rn in CK:
        X=[x for x in res if str(rn) in x['ck'] or rn in x['ck']]
        X=[x['ck'][rn] if rn in x['ck'] else x['ck'][str(rn)] for x in X]
        f=lambda s,k: sum(x[s][k] for x in X)/len(X)
        print(rn,len(X),' '.join('%s %.0f/%.0f'%(k,f('us',k),f('them',k)) for k in ['earned','mh','str','gems','trib','deaths']))
    # matched champion type comparisons at 400
    for rn in (200,400,600):
        cmp=defaultdict(list)
        for x in res:
            c=x['ck'].get(rn)
            if not c: continue
            for n,v in c['us']['byname'].items():
                if n in c['them']['byname']:
                    w=c['them']['byname'][n]; cmp[n].append((v[0]-w[0],v[1]-w[1]))
        print(rn,{n:(len(v),round(sum(a for a,b in v)/len(v)),round(sum(b for a,b in v)/len(v),1)) for n,v in cmp.items()})
