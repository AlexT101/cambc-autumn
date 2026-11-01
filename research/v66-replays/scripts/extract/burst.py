import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); us=r['us']; team={c['id']:c['team'] for c in m['champions']}
    per=defaultdict(lambda:defaultdict(float)); att=defaultdict(set)
    for e in events(d):
        if e['k'] in ('attack','cast'):
            for v,a in (e.get('dmg') or []):
                if v in team and team[v]!=team[e['a']]:
                    per[(v,e['r'])][e['a']]+=a; att[(v,e['r'])].add(e['a'])
    o=Counter()
    for (v,rn),dd in per.items():
        side='them' if team[v]==us else 'us'  # attacker side
        tot=sum(dd.values()); n=len(dd)
        o[(side,'dmg')]+=tot; o[(side,'dmg_multi')]+= tot if n>=2 else 0
        o[(side,'rounds')]+=1; o[(side,'rounds_multi')]+= n>=2
    return o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,games()))
    T=Counter()
    for o in res: T.update(o)
    for s in ('us','them'):
        print(s,'share of champion dmg delivered in target-rounds hit by >=2 attackers: %.2f ; target-rounds with >=2 attackers %.2f'%(T[(s,'dmg_multi')]/T[(s,'dmg')],T[(s,'rounds_multi')]/T[(s,'rounds')]))
