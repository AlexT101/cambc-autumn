# Allies within 8 of each off-spawn alive champion (round ends), overall and when an enemy is within 8; per team; per map.
import sys, json
from collections import defaultdict, Counter
from multiprocessing import Pool
S='replays/v66-analysis'
sys.path.insert(0,S+'/an'); sys.path.insert(0,S+'/opp')
from common import *
from feat import bfs
def one(r):
    m=meta(r['dir']); mj=mapj(m); R=rounds(r['dir']); N=len(R['round']); ch=R['champions']; us=r['us']
    D=[bfs(mj,0),bfs(mj,1)]
    nm={c['id']:c['name'] for c in m['champions']}
    pk={c['id']:((c['team'],'CI') if nm[c['id']] in ('Cassi','Issac') else c['id']) for c in ch}
    acc={'us':[0,0,0,0,0],'them':[0,0,0,0,0]}  # sum allies, n, sum allies when enemy near, n near, solo-when-enemy-near count
    for ri in range(N):
        pts=[(c['team'],(c['x'][ri],c['y'][ri]),pk[c['id']]) for c in ch if c['alive'][ri] and c['x'][ri] is not None]
        for t,p,k0 in pts:
            if D[t].get(p,99)==0: continue
            al=len({k for t2,q,k in pts if t2==t and k!=k0 and cheb(p,q)<=8})
            en=len({k for t2,q,k in pts if t2!=t and cheb(p,q)<=8})
            a=acc['us' if t==us else 'them']; a[0]+=al; a[1]+=1
            if en: a[2]+=al; a[3]+=1; a[4]+=(al==0)
    return dict(map=r['map'],opp=r['opp'],acc=acc)
if __name__=='__main__':
    with Pool(40) as p: R=p.map(one,games())
    json.dump(R,open(S+'/opp/buddies.json','w'))
    by=defaultdict(list)
    for x in R: by[x['opp']].append(x)
    for o in ['Fish','Mite','UoS','PBG']:
        s={k:[sum(x['acc'][k][i] for x in by[o]) for i in range(5)] for k in ('us','them')}
        pm=defaultdict(lambda:{'us':[0,0],'them':[0,0]})
        for x in by[o]:
            for k in ('us','them'): pm[x['map']][k][0]+=x['acc'][k][2]; pm[x['map']][k][1]+=x['acc'][k][3]
        more=sum(1 for v in pm.values() if v['them'][1] and v['us'][1] and v['them'][0]/v['them'][1]>v['us'][0]/v['us'][1])
        print(o, ' | '.join(f"{k}: allies within 8 {s[k][0]/s[k][1]:.2f} overall, {s[k][2]/s[k][3]:.2f} with enemy near; alone with enemy near {s[k][4]/s[k][3]*100:.0f}%" for k in ('us','them')), f'| maps where they have more allies near enemies: {more}/{len(pm)}')
