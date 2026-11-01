import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; mp=mapj(m); sp=mp['spawn']
    TK=defaultdict(float)
    team={c['id']:c['team'] for c in m['champions']}
    for e in events(d):
        if e['k'] in('attack','cast'):
            for v,a in (e.get('dmg') or []):
                if v in team and team[v]!=team[e['a']]: TK[(v,e['r'])]+=a
    o=Counter()
    for c in R['champions']:
        s='us' if c['team']==us else 'them'; S=sp[c['team']]
        for i in range(2,len(R['round'])):
            if not(c['alive'][i] and c['alive'][i-1] and c['alive'][i-2]): continue
            p=(c['x'][i],c['y'][i]); q=(c['x'][i-1],c['y'][i-1]); z=(c['x'][i-2],c['y'][i-2])
            if S['minX']<=p[0]<=S['maxX'] and S['minY']<=p[1]<=S['maxY']: continue
            o[(s,'turns')]+=1
            if p==z and q!=p:
                o[(s,'aba')]+=1; o[(s,'aba_dmg')]+=TK[(c['id'],R['round'][i])]
                if TK[(c['id'],R['round'][i])]>0: o[(s,'aba_hit')]+=1
    return o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,games()))
    T=Counter()
    for o in res: T.update(o)
    for s in ('us','them'): print(s,'off-spawn turns',T[(s,'turns')],'A-B-A %.3f'%(T[(s,'aba')]/T[(s,'turns')]),'per game %.0f'%(T[(s,'aba')]/412),'A-B-A turns taking champion dmg %.2f'%(T[(s,'aba_hit')]/T[(s,'aba')]),'dmg/game in ABA turns %.0f'%(T[(s,'aba_dmg')]/412))
