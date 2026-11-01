import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; NM={c['id']:c['name'] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    ch={c['id']:c for c in R['champions']}
    o=Counter()
    for e in events(d):
        if e['k'] in ('attack','cast'):
            for v,a in (e.get('dmg') or []):
                if v in team and team[v]!=team[e['a']] and NM[v] in ('Heart of Ruin','Varg'):
                    i=e['r']-2
                    if i<0: continue
                    s='us' if team[v]==us else 'them'
                    o[(s,NM[v],'hits')]+=1; o[(s,NM[v],'shielded')]+= ch[v]['shield'][i]>0
                    o[(s,NM[v],'cd_ready')]+= ch[v]['cd0' if NM[v]=='Heart of Ruin' else 'cd1'][i]==0 and ch[v]['shield'][i]<=0
        if e['k']=='camp_attack' and e.get('tgt') in team and NM[e['tgt']] in ('Heart of Ruin','Varg'):
            v=e['tgt']; i=e['r']-2; s='us' if team[v]==us else 'them'
            if i<0: continue
            o[(s,NM[v],'camphits')]+=1; o[(s,NM[v],'camp_shielded')]+= ch[v]['shield'][i]>0
    return o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,games()))
    T=Counter()
    for o in res: T.update(o)
    for s in ('us','them'):
        for nm in ('Heart of Ruin','Varg'):
            h=T[(s,nm,'hits')]; c=T[(s,nm,'camphits')]
            print(s,nm,'champ hits',h,'shield up %.2f'%(T[(s,nm,'shielded')]/h),'unshielded with shield ready %.2f'%(T[(s,nm,'cd_ready')]/h),'| camp hits',c,'shield up %.2f'%(T[(s,nm,'camp_shielded')]/c))
