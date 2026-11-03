"""Sums the AGM fuel-meter lines (aggro-x8-meter-on-x8.diff) of a bench run by aggro_possible outcome:
    python3 research/aggro-2026-11-03/agm.py aggro-x8-meter   # reads replays/fuel/games/al-<name>
"""
import zipfile,glob,statistics as st,sys
rows=[]
for b in glob.glob(f'replays/fuel/games/al-{sys.argv[1]}/*/*.repl26a'):
    z=zipfile.ZipFile(b)
    for n in z.namelist():
        if not n.endswith('stdout'): continue
        for l in z.read(n).decode(errors='replace').replace('\x00','').splitlines():
            if l.startswith('AGM '):
                try: rows.append([int(x) for x in l.split()[1:]])
                except ValueError: pass
print(len(rows),'reads')
for h in (-1,0,1):
    rs=[r for r in rows if r[9]==h]
    if not rs: continue
    ps=sorted(r[2] for r in rs)
    print(h,len(rs),'poss mean',int(st.mean(ps)),'p50',ps[len(ps)//2],'group',int(st.mean(r[3] for r in rs)),'wak',int(st.mean(r[4] for r in rs)),'rc',int(st.mean(r[6] for r in rs)),'rm',int(st.mean(r[5] for r in rs)),'fc',int(st.mean(r[7] for r in rs)))
