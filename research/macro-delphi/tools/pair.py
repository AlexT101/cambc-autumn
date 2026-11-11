import json,gzip,glob,sys,collections,zipfile,statistics as st
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
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or names[e['v']] not in ('Cassi','Issac') or 'linked' not in e: continue
        v=e['v']; r=e['r']; i=ri.get(r-1); i5=ri.get(r-5)
        if i is None or i5 is None: continue
        o=e['linked']
        cas = v if names[v]=='Cassi' else o; iss = o if cas==v else v
        sep=cheb((C[cas]['x'][i],C[cas]['y'][i]),(C[iss]['x'][i],C[iss]['y'][i]))
        at=e['at']
        en4=sum(1 for c in C if team[c]!=team[v] and C[c]['alive'][i] and cheb(at,(C[c]['x'][i],C[c]['y'][i]))<=4)
        al4=sum(1 for c in C if team[c]==team[v] and c not in (cas,iss) and C[c]['alive'][i] and cheb((C[cas]['x'][i],C[cas]['y'][i]),(C[c]['x'][i],C[c]['y'][i]))<=4)
        hp5=C[v]['hp'][i5]/C[v]['maxHp'][i5]
        out.append(dict(vic=names[v],killer=names.get(e.get('by'),'camp'),sep=sep,en4=en4,al4=al4,hp5=hp5,dec=D.get((cas,r-1),'.')+D.get((iss,r-1),'.'),r=r,gems=e['gems'],lost=(w!=team[v])))
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    res=[]
    for o in ProcessPoolExecutor(32).map(one,dirs): res+=o
    print(len(res),'pair deaths')
    print('body killed',collections.Counter(r['vic'] for r in res))
    print('killer',collections.Counter(r['killer'] for r in res).most_common(8))
    print('cassi-issac separation',sorted(collections.Counter(min(r['sep'],12) for r in res).items()))
    print('enemies within 4',sorted(collections.Counter(r['en4'] for r in res).items()))
    print('other allies within 4 of cassi',sorted(collections.Counter(r['al4'] for r in res).items()))
    print('hp 5 rounds before (victim body)',sorted(collections.Counter(round(r['hp5'],1) for r in res).items()))
    print('decisions C,I',collections.Counter(r['dec'] for r in res).most_common(10))
    print('by round',sorted(collections.Counter(r['r']//200*200 for r in res).items()))
if __name__=='__main__': main()
