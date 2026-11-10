"""nearck.py DIR: near-miss OOF turns (overrun<=5k): last passed fuel check site, its margin (fuel - need)."""
import sys,zipfile,collections
from pathlib import Path
rows=[]
for b in Path(sys.argv[1]).rglob('*.repl26a'):
    z=zipfile.ZipFile(b)
    for s in 'ab':
        try: out=z.read(f'team-{s}.stdout').replace(b'\0',b'').decode('utf-8','replace')
        except KeyError: continue
        if 'CTR ' not in out: continue
        X={}
        for l in out.splitlines():
            if l.startswith('X '):
                p=l.split()
                try: X[(int(p[1]),int(p[2]))]=100000-int(p[3])
                except (ValueError,IndexError): pass
        for l in out.splitlines():
            if not l.startswith('CTR '): continue
            p=l.split()
            try: key=(int(p[1]),int(p[2]))
            except ValueError: continue
            last=None
            for e in p[3:]:
                q=e.split(':')
                if len(q)==5 and q[0]=='c':
                    try: last=(q[1]+':'+q[2],int(q[3]),int(q[4]))
                    except ValueError: pass
            rows.append((X.get(key),last))
near=[r for r in rows if r[0] is not None and r[0]<=5000]
print('CTR turns',len(rows),'near-miss',len(near))
c=collections.Counter(r[1][0] if r[1] else '(none)' for r in near)
for site,n in c.most_common(15):
    m=sorted(r[1][1]-r[1][2] for r in near if r[1] and r[1][0]==site)
    q=lambda p: m[min(len(m)-1,int(len(m)*p))] if m else '-'
    print(f'{site:24} {n:5} ({100*n//len(near)}%)  margin p25 {q(.25)} p50 {q(.5)} p75 {q(.75)}  fuel-left p50 {sorted(r[1][1] for r in near if r[1] and r[1][0]==site)[n//2] if m else "-"}')
