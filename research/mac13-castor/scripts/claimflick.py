"""Claim flicker (C13): posted claims (D lines' claim) that change and change back within 3 rounds, by the branch held between."""
import zipfile,re,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
DP=re.compile(rb'^[\s\0]*DP (\d+) (\d+) (\d+) ', re.M)
T='Ryth Vesper Vendetta Cassi Issac Stellar Prism Marcella Willow Ren Varg Tavi HoR'.split()
def one(job):
    rp,t=job; c=collections.Counter()
    try: out=zipfile.ZipFile(rp).read(f'team-{t}.stdout')
    except Exception: return c
    typ={int(m.group(2)):T[int(m.group(3))] for m in DP.finditer(out)}
    seq=collections.defaultdict(list)
    for m in D.finditer(out): seq[int(m.group(2))].append((int(m.group(1)),m.group(3).decode(),int(m.group(4)),int(m.group(5))))
    for h,L in seq.items():
        ty=typ.get(h,'?')
        for i in range(1,len(L)):
            r,b,fg,cl=L[i]; r0,b0,fg0,cl0=L[i-1]
            if r!=r0+1 or cl==cl0: continue
            c[(ty,'chg')]+=1
            c[(ty,'chg_br',b0+b)]+=1
            for j in range(i+1,min(i+3,len(L))):
                if L[j][3]==cl0 and L[j][0]-r0<=3:
                    c[(ty,'flick')]+=1; c[(ty,'flick_br',b0+b+L[j][1])]+=1
                    if cl==-1 or cl0==-1: c[(ty,'flick_none')]+=1
                    break
    return c
if __name__=='__main__':
    d=sys.argv[1]; jobs=[]
    for line in open(d+'/manifest.txt'):
        a,b,_,rp=line.split()
        if os.path.exists(rp): jobs.append((rp,'a' if 'c13-dither' in os.path.basename(a) else 'b'))
    tot=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for c in ex.map(one,jobs,chunksize=8): tot+=c
    print(len(jobs),'games')
    for ty in sorted({k[0] for k in tot}):
        ch=tot[(ty,'chg')] or 1
        print(ty,'claim changes',tot[(ty,'chg')],'flick back<=3',f"{100*tot[(ty,'flick')]/ch:.1f}%",'to/from none',tot[(ty,'flick_none')])
        print('   branches(prev,now,back):',', '.join(f"{k[2]}:{v}" for k,v in sorted(((k,v) for k,v in tot.items() if k[0]==ty and k[1]=='flick_br'),key=lambda x:-x[1])[:8]))
    al=sum(v for k,v in tot.items() if k[1]=='chg'); fl=sum(v for k,v in tot.items() if k[1]=='flick')
    print('ALL',al,fl,f"{100*fl/al:.1f}%")
    agg=collections.Counter()
    for k,v in tot.items():
        if k[1]=='flick_br': agg[k[2]]+=v
    print(agg.most_common(15))
