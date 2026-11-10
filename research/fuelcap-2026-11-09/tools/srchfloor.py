import sys,zipfile
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/cambc-autumn/tools/fuel/census')
from census import parse_line
oof=[];fin=[];allfin_search=0
for b in Path(sys.argv[1]).rglob('*.repl26a'):
    z=zipfile.ZipFile(b)
    for s in 'ab':
        try: out=z.read(f'team-{s}.stdout').replace(b'\0',b'').decode('utf-8','replace')
        except KeyError: continue
        if 'SRCH ' not in out: continue
        X={}; S={}; C={}
        for l in out.splitlines():
            p=l.split()
            try:
                if l.startswith('X '): X[(int(p[1]),int(p[2]))]=100000-int(p[3])
                elif l.startswith('SRCH ') and len(p)>5 and p[3]=='fuel':
                    f=dict(zip(p[3::2],p[4::2])); S[(int(p[1]),int(p[2]))]=(int(f['left']),int(f['fuel']),int(f['grow'])+int(f['price']))
                elif l.startswith('CEN ') and ' | ' in l:
                    r=parse_line(l); C[(r['round'],r['champ'])]=r
            except Exception: pass
        for k,(left,used,gp) in S.items():
            end=left-used
            if k in X and k in C and C[k]['oof'] and not C[k]['late']: oof.append((end,gp,X[k]))
            elif k in C and not C[k]['oof'] and not C[k]['late']: fin.append((end,gp,(C[k]['start']-C[k]['spent'])))
            elif k not in X: allfin_search+=1
print('OOF-first with search',len(oof),'(near<=5k',sum(1 for o in oof if o[2]<=5000),') heavy finished with search',len(fin),'other searches',allfin_search)
import statistics
fp=sorted(e-t for e,_,t in fin); print('finished heavy: spend after search p50 %d p90 %d p99 %d'%(fp[len(fp)//2],fp[int(.9*len(fp))],fp[int(.99*len(fp))]))
for F in range(10000,50001,5000):
    def save(e,gp): return max(0,min(gp,F-e)) if e<F else 0   # grow+price spend below F
    resc=sum(1 for e,gp,o in oof if save(e,gp)>=o+1000)
    hit=sum(1 for e,gp,t in fin if e<F); hitall=hit
    print(f'F={F}: OOF rescued (savings >= overrun+1k) {resc} of {len(oof)}; heavy finished searches touched {hit} ({100*hit/len(fin):.1f}%)')
