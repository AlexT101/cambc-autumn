"""cenjoin.py DIR: OOF-first CEN turns joined to their overrun (X line); innermost and decide-level scope for near misses."""
import sys,collections,re
sys.path.insert(0,'/home/ubuntu/cambc-autumn/tools/fuel/census')
import zipfile
from pathlib import Path
from census import parse_line
rows=[]
for b in Path(sys.argv[1]).rglob('*.repl26a'):
    z=zipfile.ZipFile(b)
    for s in 'ab':
        try: out=z.read(f'team-{s}.stdout').replace(b'\0',b'').decode('utf-8','replace')
        except KeyError: continue
        if 'CEN ' not in out: continue
        X={}
        for l in out.splitlines():
            if l.startswith('X '):
                p=l.split()
                try: X[(int(p[1]),int(p[2]))]=100000-int(p[3])
                except (ValueError,IndexError): pass
        for l in out.splitlines():
            if l.startswith('CEN ') and ' | ' in l:
                try: r=parse_line(l)
                except Exception: continue
                if r['oof'] and not r['late']:
                    r['over']=X.get((r['round'],r['champ'])); rows.append(r)
print('OOF-first',len(rows),'joined',sum(1 for r in rows if r['over'] is not None))
def tab(title,rs,key,n=18):
    c=collections.Counter(key(r) for r in rs)
    print(f'{title} ({len(rs)}):',', '.join(f'{k} {v} ({100*v//max(1,len(rs))}%)' for k,v in c.most_common(n)))
DEC={'goal','act_end','decide_main','turn_order','strike_after','chase','see_revealed','publish_order','route','local_support','want_home','post_search','strike_search','support_work','channels','world','comms send','queue','turn end'}
def inner(r): return r['stack'].split('/')[-1]
def declevel(r):
    fr=r['stack'].split('/')
    for f in fr:
        if f in DEC: return f
    return fr[-1] if fr else '?'
for lo,hi in ((0,5000),(5000,20000),(20000,10**9)):
    rs=[r for r in rows if r['over'] is not None and lo<r['over']<=hi]
    print(f'\n== overrun {lo}-{hi}')
    tab(' decide-level',rs,declevel)
    tab(' innermost',rs,inner)
    tab(' 2 innermost',rs,lambda r:'/'.join(r['stack'].split('/')[-2:]),12)
