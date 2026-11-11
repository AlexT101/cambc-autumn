import json,gzip,glob,sys,collections,zipfile
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; ROOT='/home/ubuntu/wt/macro-o4/'
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json')); w=M['result']['winner']
    src=M['sources'][0]['source']
    names={c['id']:c['name'] for c in M['champions']}
    team={c['id']:c['team'] for c in M['champions']}
    z=zipfile.ZipFile(ROOT+src)
    D={}
    for t,f in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        for line in z.read(f).decode(errors='replace').splitlines():
            p=line.split()
            if len(p)>=4 and p[0]=='D': D[(int(p[2]),int(p[1]))]=p[3]
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    C={c['id']:c for c in R['champions']}
    out=collections.Counter()
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('by') is None: continue
        v=e['v']; r=e['r']; dec=D.get((v,r-1),'.')
        if dec not in 'RF': continue
        # find when the R streak started
        r0=r-1
        while D.get((v,r0-1))==dec and r0>r-40: r0-=1
        i=ri.get(r0)
        if i is None: continue
        at=(C[v]['x'][i],C[v]['y'][i])
        al=[c for c in C if team[c]==team[v] and c!=v and C[c]['alive'][i] and cheb(at,(C[c]['x'][i],C[c]['y'][i]))<=8]
        en=[c for c in C if team[c]!=team[v] and C[c]['alive'][i] and cheb(at,(C[c]['x'][i],C[c]['y'][i]))<=8]
        aldec=''.join(sorted(D.get((c,r0),'.') for c in al))
        out[(dec,'streak',min(r-r0,10))]+=1
        out[(dec,'al',len(al),'en',len(en))]+=1
        hpf=C[v]['hp'][i]/max(1,C[v]['maxHp'][i])
        out[(dec,'hp', round(hpf,1))]+=1
        for ch in aldec: out[(dec,'allydec',ch)]+=1
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.Counter()
    for o in ProcessPoolExecutor(32).map(one,dirs): agg.update(o)
    for k in sorted(agg): print(k, agg[k])
if __name__=='__main__': main()
