"""Print example 'alive group unworked, ally walks to a dead target' cases for one game."""
import sys, json
import extract_study as X
from collections import Counter
dirs=sorted({r['dir'] for r in json.loads((X.AN/'index.json').read_text())['games']})
d=dirs[int(sys.argv[1]) if len(sys.argv)>1 else 5]
g=X.Game(d); mp=g.map; N=len(g.rounds['round'])
src=X.WT/[s['source'] for s in g.meta['sources'] if s['source'].endswith('-12.repl26a')][0]
D,_=X.parse_D(src)
bl=set(mp.walls)|set(mp.holes)|set(mp.altars)
gd={grp['id']:X.bfs(mp,grp['tiles'],bl) for grp in mp.groups}
rows=sorted(g.rounds['groups'],key=lambda x:x[0]); ng=len(mp.groups)
st=[[None]*ng for _ in range(N+2)]; cur=[None]*ng; k=0
for r in range(1,N+2):
    while k<len(rows) and rows[k][0]<=r-1: cur[rows[k][1]]=rows[k]; k+=1
    st[r]=list(cur)
hits={}
for e in g.events:
    if e['k'] in('attack','cast') and e.get('cdmg'):
        for cc,_ in e['cdmg']: hits.setdefault(e['r'],set()).add(next(c['group'] for c in mp.camps if c['id']==cc))
print(g.map_name, d)
n=0
for r in range(50,N,7):
    for gi in range(ng):
        row=st[r][gi]
        if not row or row[2]!=1 or mp.groups[gi]['gems']==0 or 'Monolith' in mp.groups[gi]['types'] or gi in hits.get(r,()): continue
        for t in (0,1):
            if any(D.get((r,c),(0,-9))[1]==gi for c in g.team_ids[t]): continue
            for c in g.team_ids[t]:
                p=g.pos(c,r-2)
                if not p or gd[gi].get(p,99)>12: continue
                x=D.get((r,c))
                if not x or x[0]!='F' or x[1]<0: continue
                fr=st[r][x[1]]
                if fr and fr[2]!=1:
                    n+=1
                    if n<=14:
                        print(f"r{r} t{t} {g.name_of[c]} at {p}: alive g{gi} {sorted(Counter(mp.groups[gi]['types']).items())} awake={row[6]} hp={row[7]} dist {gd[gi][p]} | target g{x[1]} {''.join(sorted(set(a[0] for a in mp.groups[x[1]]['types'])))} state {fr[2]} resp {fr[5]} dist {gd[x[1]].get(p)}")
                    break
print('n',n)
