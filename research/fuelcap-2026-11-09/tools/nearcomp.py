"""nearcomp.py DIR: mean self fuel per component on near-miss OOF turns with no late gate vs heavy finished turns."""
import sys,zipfile,collections
sys.path.insert(0,'/home/ubuntu/cambc-autumn/tools/fuel/census')
from census import parse_line
from pathlib import Path
near=[];fin=[]
for b in Path(sys.argv[1]).rglob('*.repl26a'):
    z=zipfile.ZipFile(b)
    for s in 'ab':
        try: out=z.read(f'team-{s}.stdout').replace(b'\0',b'').decode('utf-8','replace')
        except KeyError: continue
        if 'CEN ' not in out: continue
        X={}; last={}
        for l in out.splitlines():
            p=l.split()
            if l.startswith('X '):
                try: X[(int(p[1]),int(p[2]))]=100000-int(p[3])
                except (ValueError,IndexError): pass
            elif l.startswith('CTR '):
                try: key=(int(p[1]),int(p[2]))
                except ValueError: continue
                lc=None
                for e in p[3:]:
                    q=e.split(':')
                    if len(q)==5 and q[0]=='c': lc=q[1]+':'+q[2]
                last[key]=lc
        for l in out.splitlines():
            if l.startswith('CEN ') and ' | ' in l:
                try: r=parse_line(l)
                except Exception: continue
                k=(r['round'],r['champ'])
                if r['oof'] and not r['late']:
                    o=X.get(k)
                    if o is not None and o<=5000 and last.get(k) in (None,'escape.cc:588'): near.append(r)
                elif not r['oof'] and not r['late'] and r['spent']>=85000: fin.append(r)
print('near-miss ungated',len(near),'finished 85k+',len(fin))
def agg(rs):
    a=collections.Counter(); w=collections.Counter()
    for r in rs:
        for k,(inc,sf,n) in r['c'].items(): a[k]+=sf; w[k]+=1
    return {k:(a[k]/len(rs),100*w[k]/len(rs)) for k in a}
A=agg(near); B=agg(fin)
print(f"{'component':22} {'near self/turn':>14} {'ran%':>5} {'fin85 self/turn':>15} {'ran%':>5}")
for k,(v,p) in sorted(A.items(),key=lambda x:-x[1][0])[:28]:
    bv,bp=B.get(k,(0,0)); print(f'{k:22} {v:14.0f} {p:5.0f} {bv:15.0f} {bp:5.0f}')
import statistics


