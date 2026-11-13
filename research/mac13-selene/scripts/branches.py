import zipfile, re, sys, os, json
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
def one(p):
    try:
        z=zipfile.ZipFile(p); c=Counter()
        for nm in z.namelist():
            if nm.endswith('.stdout'):
                for m in D.finditer(z.read(nm)): c[(int(m.group(2)), m.group(3).decode())]+=1
        return c
    except Exception as e: return Counter()
if __name__=='__main__':
    B=sys.argv[1]; fs=[os.path.join(B,f) for f in os.listdir(B) if f.endswith('.repl26a')]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for c in ex.map(one,fs,chunksize=8):
            for (cid,b),n in c.items(): tot[b]+=n
    s=sum(tot.values()); print('D lines',s, 'games', len(fs))
    for b,n in tot.most_common(): print(b, f"{100*n/s:.1f}%")
