import zipfile, re, sys, os
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
def one(p):
    try:
        z=zipfile.ZipFile(p); seq=defaultdict(list)
        for nm in z.namelist():
            if nm.endswith('.stdout'):
                for m in D.finditer(z.read(nm)):
                    seq[int(m.group(2))].append((int(m.group(1)), m.group(3).decode(), int(m.group(4)), int(m.group(5))))
        res=Counter()
        for cid,s in seq.items():
            prev=None; run=0
            for r,b,fg,cl in s:
                if b!='F': continue
                res['F']+=1
                if prev is not None and fg!=prev:
                    res['switch']+=1
                    if run<=3: res['switch_short']+=1
                prev=fg; run=run+1 if fg==prev else 1
            # A-B-A flips
            fl=[x[2] for x in s if x[1]=='F']
            comp=[fl[0]] if fl else []
            for g in fl[1:]:
                if g!=comp[-1]: comp.append(g)
            res['aba']+=sum(1 for i in range(2,len(comp)) if comp[i]==comp[i-2])
            res['segments']+=len(comp)
        return res
    except Exception as e: return Counter()
if __name__=='__main__':
    B=sys.argv[1]; fs=[os.path.join(B,f) for f in os.listdir(B) if f.endswith('.repl26a')]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for c in ex.map(one,fs,chunksize=8): tot.update(c)
    print({k:v/len(fs)/10 for k,v in tot.items()}, 'per champion-game')
