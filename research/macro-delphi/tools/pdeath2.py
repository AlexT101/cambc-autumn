import json,gzip,glob,sys,collections,zipfile
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; ROOT='/home/ubuntu/wt/macro-o4/'
def one(d):
    M=json.load(open(d+'/meta.json'))
    src=M['sources'][0]['source']
    names={c['id']:c['name'] for c in M['champions']}
    team={c['id']:c['team'] for c in M['champions']}
    z=zipfile.ZipFile(ROOT+src)
    D={}
    for t,f in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        for line in z.read(f).decode(errors='replace').splitlines():
            p=line.split()
            if len(p)>=4 and p[0]=='D':
                D[(int(p[2]),int(p[1]))]=p[3]
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or names.get(e['v'])!='Prism': continue
        v=e['v']; r=e['r']
        seq=''.join(D.get((v,rr),'.') for rr in range(r-6,r+1))
        out.append((seq, e['gems']))
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    rows=[]
    with ProcessPoolExecutor(32) as ex:
        for o in ex.map(one,dirs): rows+=o
    c=collections.Counter(s[-2:] for s,_ in rows); print('last two decisions',c.most_common(15))
    c=collections.Counter(s for s,_ in rows); print(c.most_common(25))
    c=collections.Counter(ch for s,_ in rows for ch in s); print(c.most_common())
if __name__=='__main__': main()
