import json,gzip,glob,sys,collections,zipfile
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; ROOT='/home/ubuntu/wt/macro-o4/'
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json')); w=M['result']['winner']
    names={c['id']:c['name'] for c in M['champions']}
    team={c['id']:c['team'] for c in M['champions']}
    src=M['sources'][0]['source']; z=zipfile.ZipFile(ROOT+src); D={}
    for t,f in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        for line in z.read(f).decode(errors='replace').splitlines():
            p=line.split()
            if len(p)>=4 and p[0]=='D': D[(int(p[2]),int(p[1]))]=p[3]
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    C={c['id']:c for c in R['champions']}
    mp=json.load(open(d+'/'+M['mapFile'])) if False else None
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e.get('by') is not None and team.get(e['by'])!=team[e['v']]:
            v=e['v']; k=e['by']; r=e['r']; i=ri.get(r-3)
            if i is None: return None
            at=e['at']
            na=sum(1 for c in C if team[c]==team[v] and c!=v and C[c]['alive'][i] and cheb(at,(C[c]['x'][i],C[c]['y'][i]))<=8)
            ne=sum(1 for c in C if team[c]!=team[v] and C[c]['alive'][i] and cheb(at,(C[c]['x'][i],C[c]['y'][i]))<=8)
            vdec=''.join(D.get((v,rr),'.') for rr in range(r-8,r))
            return dict(vic=names[v],killer=names[k],na=na,ne=ne,vdec=vdec,r=r,gems=e['gems'])
    return None
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    res=[o for o in ProcessPoolExecutor(32).map(one,dirs) if o]
    print(collections.Counter(r['vic'] for r in res).most_common())
    print(collections.Counter(r['killer'] for r in res).most_common())
    print('victim allies within 8 vs enemies:',sorted(collections.Counter((r['na'],r['ne']) for r in res).items()))
    print(collections.Counter(r['vdec'][-4:] for r in res).most_common(15))
if __name__=='__main__': main()
