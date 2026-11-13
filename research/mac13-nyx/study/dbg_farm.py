import sys, json
sys.argv=['x']
import extract_study as X
from collections import Counter
d=sorted({r['dir'] for r in json.loads((X.AN/'index.json').read_text())['games']})[3]
g=X.Game(d); mp=g.map
src=X.WT/[s['source'] for s in g.meta['sources'] if s['source'].endswith('-12.repl26a')][0]
D,_=X.parse_D(src)
blocked=set(mp.walls)|set(mp.holes)|set(mp.altars)
gd={grp['id']:X.bfs(mp,grp['tiles'],blocked) for grp in mp.groups}
c=Counter(); far=Counter()
for (r,cid),(ch,fg,cl) in D.items():
    if ch!='F': continue
    c[fg>=0]+=1
    if fg>=0 and r>1:
        p=g.pos(cid,r-2)
        if p: far[min(gd[fg].get(p,99),30)//5]+=1
print(c, sorted(far.items()))
# example sequence for one champion
cid=g.team_ids[0][0]
print(''.join(D.get((r,cid),('?',))[0] for r in range(1,200)))
print([D.get((r,cid),(0,-9))[1] for r in range(1,200)])
print([gd[D[(r,cid)][1]].get(g.pos(cid,r-2),99) if D[(r,cid)][1]>=0 and r>1 and g.pos(cid,r-2) else None for r in range(1,200)])
