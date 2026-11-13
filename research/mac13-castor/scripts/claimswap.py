"""C13: ally-claim switches where the ally re-picked in farm: did we and it swap groups?"""
import zipfile,re,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
FS=re.compile(rb'^[\s\0]*FS (\d+) (\d+) (-?\d+) (-?\d+) (\S) (\d+) ', re.M)
def one(job):
    rp,t=job; c=collections.Counter()
    out=zipfile.ZipFile(rp).read(f'team-{t}.stdout')
    d={}
    for m in D.finditer(out): d[(int(m.group(1)),int(m.group(2)))]=(m.group(3).decode(),int(m.group(5)))
    hs={h for (_,h) in d}
    for m in FS.finditer(out):
        r,h,p,b,mask=int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4)),int(m.group(6))
        if not mask&4: continue
        for a in hs-{h}:
            for rr in (r-1,r):
                x=d.get((rr,a)); y=d.get((rr-1,a))
                if not x or not y or x[1]==y[1] or x[0]!='F' or y[0]!='F': continue
                c['ff']+=1
                if x[1]==p: c['ally took our prev']+=1
                if y[1]==b: c['we took ally old']+=1
                if x[1]==p and y[1]==b: c['swap']+=1
                if x[1]==b: c['we join ally new']+=1
    return c
if __name__=='__main__':
    dd=sys.argv[1]; jobs=[]
    for line in open(dd+'/manifest.txt'):
        a,b,_,rp=line.split(); jobs.append((rp,'a' if sys.argv[2] in os.path.basename(a) else 'b'))
    tot=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for c in ex.map(one,jobs,chunksize=8): tot+=c
    print(tot)
