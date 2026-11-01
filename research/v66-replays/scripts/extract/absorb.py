import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
# per champion: walk events in order, track live shield: shield cast sets shield to value from rounds (approx: read shield at round end after the cast round)...
# simpler: hp lost per hit = from death/hp trajectory is hard; instead use rounds: per round, hp drop vs champion damage taken in that round.
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; team={c['id']:c['team'] for c in m['champions']}
    taken=defaultdict(Counter)
    for e in events(d):
        if e['k'] in ('attack','cast'):
            for v,a in (e.get('dmg') or []):
                if v in team and team[v]!=team[e['a']]: taken[v][e['r']]+=a
    o=Counter()
    for c in R['champions']:
        side='us' if c['team']==us else 'them'
        for i in range(1,len(R['round'])):
            rn=R['round'][i]; t=taken[c['id']].get(rn,0)
            if t<=0 or not c['alive'][i-1]: continue
            sh_before=c['shield'][i-1]
            o[(side,'dmg')]+=t; o[(side,'absorbed_ub')]+=min(t,sh_before)
    return r['opp'],o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,games()))
    T=defaultdict(Counter)
    for op,o in res: T[op].update(o); T['ALL'].update(o)
    for op in ('Fish','Mite','UoS','PBG','ALL'):
        o=T[op]
        print('%-4s dmg taken by us %8.0f, absorbed by our shields (start-of-round shield) %.2f | dmg taken by them %8.0f absorbed %.2f'%(op,o[('us','dmg')],o[('us','absorbed_ub')]/o[('us','dmg')],o[('them','dmg')],o[('them','absorbed_ub')]/o[('them','dmg')]))
