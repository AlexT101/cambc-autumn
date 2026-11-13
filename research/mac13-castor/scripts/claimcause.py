"""C13: for FS switches whose mask says an ally's claim changed, what the allies' D lines did between our last turn and this one."""
import zipfile,re,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
FS=re.compile(rb'^[\s\0]*FS (\d+) (\d+) (-?\d+) (-?\d+) (\S) (\d+) ', re.M)
def one(job):
    rp,t=job; c=collections.Counter()
    try: out=zipfile.ZipFile(rp).read(f'team-{t}.stdout')
    except Exception: return c
    d={}
    for m in D.finditer(out): d[(int(m.group(1)),int(m.group(2)))]=(m.group(3).decode(),int(m.group(5)))
    hs={h for (_,h) in d}
    for m in FS.finditer(out):
        r,h,mask=int(m.group(1)),int(m.group(2)),int(m.group(6))
        if not mask&4: continue
        c['claim']+=1
        why=set()
        for a in hs-{h}:
            for rr in (r-1,r):
                x=d.get((rr,a)); y=d.get((rr-1,a))
                if not x or not y or x[1]==y[1]: continue
                if x[0]=='R' or y[0]=='R': why.add('ally retreat')
                elif -1 in (x[1],y[1]): why.add('ally to/from none (other branch '+x[0]+')')
                else: why.add('ally re-pick '+y[0]+x[0])
        k=min(why) if len(why)==1 else ('ally retreat' if 'ally retreat' in why else 'several')
        if not why: k='unseen (earlier)'
        c[k]+=1
    return c
if __name__=='__main__':
    dd=sys.argv[1]; jobs=[]
    for line in open(dd+'/manifest.txt'):
        a,b,_,rp=line.split()
        if os.path.exists(rp): jobs.append((rp,'a' if sys.argv[2] in os.path.basename(a) else 'b'))
    tot=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for c in ex.map(one,jobs,chunksize=8): tot+=c
    n=tot.pop('claim')
    print(n,'ally-claim switches')
    for k,v in tot.most_common(14): print(f'  {k}: {100*v/n:.1f}%')
