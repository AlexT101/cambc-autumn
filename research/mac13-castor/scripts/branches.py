import zipfile,glob,re,collections,sys
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
def one(p):
    c=collections.Counter()
    try:
        z=zipfile.ZipFile(p)
        for n in z.namelist():
            if n.endswith('stdout'):
                for m in D.finditer(z.read(n)):
                    r=int(m.group(1)); ph='early' if r<=300 else 'late'
                    c[(ph,m.group(3).decode())]+=1
    except Exception as e: pass
    return c
if __name__=='__main__':
    fs=glob.glob(sys.argv[1]+'/*.repl26a')
    tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for c in ex.map(one,fs,chunksize=8): tot+=c
    for ph in ('early','late'):
        n=sum(v for (p,b),v in tot.items() if p==ph)
        print(ph, ' '.join(f"{b}:{100*v/n:.1f}" for (p,b),v in sorted(tot.items(),key=lambda x:-x[1]) if p==ph))
