import sys; sys.path.insert(0,sys.argv[1])
from common import *
import statistics as st
D=json.load(open(sys.argv[1]+'/deaths.json'))
by=defaultdict(list)
for d in D: by[d['key']].append(d)
G={g['dir']:g for g in games()}
rows=[]
for k,g in G.items():
    ds=sorted([d for d in by.get(k,[]) if d['killer']!='camp'],key=lambda d:d['r'])
    if not ds: continue
    fb=ds[0]
    m=meta(k); mp=mapj(m); us=g['us']
    F=[spawn_field(mp,0),spawn_field(mp,1)]
    t=us if fb['side']=='us' else 1-us
    at=tuple(fb.get('at',(0,0))) if 'at' in fb else None
    rows.append((fb['side'],fb['victim'],fb['killer'],fb['r'],fb['near1'],fb['farmed'],fb['campdmg'],fb['hp15'],g['opp'],g['map'],fb['src']))
X=[r for r in rows if r[0]=='us']; Y=[r for r in rows if r[0]=='them']
print('first deaths ours',len(X),'theirs',len(Y))
for nm,Z in (('ours',X),('theirs',Y)):
    print(nm,'victim',Counter(r[1] for r in Z).most_common(6))
    print(nm,'killer',Counter(r[2] for r in Z).most_common(6))
    print(nm,'near (allies,enemies)',Counter(tuple(r[4]) for r in Z).most_common(8))
    print(nm,'farmed in last 15: %.2f  campdmg>200: %.2f  hp15 median %.2f'%(sum(r[5]>0 for r in Z)/len(Z),sum(r[6]>200 for r in Z)/len(Z),st.median([r[7] for r in Z if r[7] is not None])))
print('ours by opp',Counter(r[8] for r in X), 'theirs by opp',Counter(r[8] for r in Y))
# per-map: maps where we die first in all games vs not
pm=defaultdict(lambda:[0,0])
for r in rows: pm[r[9]][r[0]=='us']+=1
print('maps where we die first share:',sorted(((round(v[1]/(v[0]+v[1]),2),k) for k,v in pm.items())))
