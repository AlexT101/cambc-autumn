"""Decision branch shares from D trace lines in replays' team stdout (debug builds), rounds <= END, by phase."""
import zipfile,glob,re,sys,collections
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$',re.M)
def one(p):
    c=collections.Counter()
    try: z=zipfile.ZipFile(p)
    except Exception: return c
    for n in z.namelist():
        if n.endswith('.stdout'):
            for m in D.finditer(z.read(n)):
                r=int(m.group(1)); ph='r1-150' if r<=150 else 'r151-400' if r<=400 else 'r401+'
                c[(ph,m.group(3).decode())]+=1
    return c
if __name__=='__main__':
    ps=glob.glob(sys.argv[1]+'/*.repl26a')
    tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for c in ex.map(one,ps,chunksize=8): tot.update(c)
    for ph in ('r1-150','r151-400','r401+'):
        s=sum(v for (p,b),v in tot.items() if p==ph)
        print(ph,' '.join('%s %.1f%%'%(b,100*v/s) for (p,b),v in sorted(tot.items(),key=lambda kv:-kv[1]) if p==ph and v/s>0.004))
