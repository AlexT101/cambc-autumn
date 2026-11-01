import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; team={c['id']:c['team'] for c in m['champions']}
    CH={c['id']:c for c in R['champions']}; ri={rn:i for i,rn in enumerate(R['round'])}
    firsthit={}
    ev=events(d); out=[]
    hits=defaultdict(list)
    for e in ev:
        if e['k'] in('attack','cast'):
            for v,a in (e.get('dmg') or []):
                if v in team and team[v]!=team[e['a']]: hits[(e['a'],v)].append(e['r'])
    for e in ev:
        if e['k']!='death' or e.get('linked') is not None or e.get('by') is None: continue
        v,k,rn=e['v'],e['by'],e['r']
        hs=[x for x in hits[(k,v)] if rn-30<=x<=rn]
        if not hs: continue
        h0=min(hs)
        # walk back from h0: rounds the victim continuously saw the killer before first hit
        n=0; i=ri[h0]
        while i>0 and k in CH[v]['sees'][i] and n<40: n+=1; i-=1
        dist=None
        j=ri[h0]-1
        if j>=0 and CH[k]['alive'][j] and CH[v]['alive'][j]: dist=cheb((CH[k]['x'][j],CH[k]['y'][j]),(CH[v]['x'][j],CH[v]['y'][j]))
        out.append(('us' if team[v]==us else 'them',n,dist,m['champions'][k]['name']))
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,games()) for x in o]
    for s in ('us','them'):
        X=[x for x in res if x[0]==s]
        c=Counter(min(x[1],6) for x in X)
        print(s,len(X),'rounds killer seen continuously before its first hit:',{k:'%.2f'%(v/len(X)) for k,v in sorted(c.items())})
