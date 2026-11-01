import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); us=r['us']; NM={c['id']:c['name'] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    o=Counter()
    for e in events(d):
        if e['k']=='cast':
            s='us' if team[e['a']]==us else 'them'; nm=NM[e['a']]; ab=e.get('ab')
            hitc=[a for v,a in (e.get('dmg') or []) if v in team and team[v]!=team[e['a']]]
            st=[v for v in (e.get('stun') or []) if v in team and team[v]!=team[e['a']]]
            o[(s,nm,ab,'n')]+=1
            o[(s,nm,ab,'champhit')]+= bool(hitc)
            o[(s,nm,ab,'champdmg')]+= sum(hitc)
            o[(s,nm,ab,'stuns')]+= len(st)
            o[(s,nm,ab,'camp')]+= bool(e.get('cdmg'))
    return o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,games()))
    T=Counter()
    for o in res: T.update(o)
    keys=sorted({k[:3] for k in T})
    G=Counter()
    for r in games():
        for c in meta(r['dir'])['champions']: G[('us' if c['team']==r['us'] else 'them',c['name'])]+=1
    for k in keys:
        if T[k+('n',)]<300: continue
        n=T[k+('n',)]; g=G[k[:2]]
        print('%-4s %-14s %-13s casts/g %5.1f  champhit %.2f  dmg/champcast %5.0f  stuns/g %4.1f  camp %.2f'%(k[0],k[1],k[2],n/g,T[k+('champhit',)]/n,T[k+('champdmg',)]/max(1,T[k+('champhit',)]),T[k+('stuns',)]/g,T[k+('camp',)]/n))
