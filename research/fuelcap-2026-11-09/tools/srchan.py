import sys,zipfile,collections
from pathlib import Path
def q(v,ps=(50,90,99)):
    v=sorted(v); return ' '.join(f'p{p}={v[min(len(v)-1,int(len(v)*p/100))]}' for p in ps) if v else '-'
near=[];allS=[]
for b in Path(sys.argv[1]).rglob('*.repl26a'):
    z=zipfile.ZipFile(b)
    for s in 'ab':
        try: out=z.read(f'team-{s}.stdout').replace(b'\0',b'').decode('utf-8','replace')
        except KeyError: continue
        if 'SRCH ' not in out: continue
        X={}; S={}
        for l in out.splitlines():
            p=l.split()
            try:
                if l.startswith('X '): X[(int(p[1]),int(p[2]))]=100000-int(p[3])
                elif l.startswith('SRCH ') and len(p)>5 and p[3]=='fuel':
                    f=dict(zip(p[3::2],p[4::2])); f={k:int(v,16) if k=='rm' else int(v) if v.lstrip('-').isdigit() else v for k,v in f.items()}
                    S[(int(p[1]),int(p[2]))]=f; allS.append(f)
            except (ValueError,IndexError): pass
        for k,o in X.items():
            if o<=5000 and k in S: near.append(S[k])
print('searches',len(allS),'on near-miss OOF turns',len(near))
for name,rs in (('all',allS),('near',near)):
    print(name)
    for k in ('fuel','read','grow','price','act','nodes','offers','tiles','priced','queries','foes','units','leaves','left','capped','mates'):
        print(f'  {k:8}',q([r[k] for r in rs if isinstance(r.get(k),int)]))
