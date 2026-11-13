"""C13: lengths of consecutive retreat ('R') runs in D lines, and the branch after."""
import zipfile,re,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) ', re.M)
def one(job):
    rp,t=job; c=collections.Counter()
    out=zipfile.ZipFile(rp).read(f'team-{t}.stdout')
    seq=collections.defaultdict(list)
    for m in D.finditer(out): seq[int(m.group(2))].append(m.group(3).decode())
    for L in seq.values():
        n=0
        for i,b in enumerate(L):
            if b=='R': n+=1
            elif n:
                c[(min(n,10),b)]+=1; n=0
    return c
if __name__=='__main__':
    dd=sys.argv[1]; jobs=[]
    for line in open(dd+'/manifest.txt'):
        a,b,_,rp=line.split(); jobs.append((rp,'a' if sys.argv[2] in os.path.basename(a) else 'b'))
    tot=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for c in ex.map(one,jobs,chunksize=8): tot+=c
    N=sum(tot.values())
    for n in range(1,11):
        s=sum(v for k,v in tot.items() if k[0]==n)
        print(n, f"{100*s/N:.1f}%", 'then', ' '.join(f"{k[1]}:{v}" for k,v in sorted(((k,v) for k,v in tot.items() if k[0]==n),key=lambda x:-x[1])[:5]))
