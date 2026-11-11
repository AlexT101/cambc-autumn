import json,gzip,glob,sys,collections,zipfile
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; ROOT='/home/ubuntu/wt/macro-o4/'
def one(d):
    M=json.load(open(d+'/meta.json')); w=M['result']['winner']
    src=M['sources'][0]['source']
    names={c['id']:c['name'] for c in M['champions']}
    team={c['id']:c['team'] for c in M['champions']}
    z=zipfile.ZipFile(ROOT+src)
    D={}; Estart={}
    for t,f in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        for line in z.read(f).decode(errors='replace').splitlines():
            p=line.split()
            if len(p)>=4 and p[0]=='D':
                D[(int(p[2]),int(p[1]))]=p[3]
                if p[3]=='E': Estart.setdefault(team[int(p[2])], int(p[1]))
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    out=[]
    for t,r0 in Estart.items():
        i=ri[r0]
        out.append(dict(team=t, r0=r0, won=(w==t), end=M['result']['rounds'], sc=R['gems'][t][i], esc=R['gems'][1-t][i]))
    deaths=collections.Counter()
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death':
            v=e['v']; dec=D.get((v,e['r']-1),'.')
            deaths[(dec, w==team[v])]+=1
    return out,deaths
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    rows=[]; dd=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for o,dc in ex.map(one,dirs): rows+=o; dd.update(dc)
    print(len(rows),'team-games with an E branch; of those won %.1f%%'%(100*sum(r['won'] for r in rows)/len(rows)))
    import statistics as st
    print('E start: median rounds before end', st.median(r['end']-r['r0'] for r in rows), 'our score',st.median(r['sc'] for r in rows),'their',st.median(r['esc'] for r in rows))
    print('deaths by decision the round before (dec, victim team won):', dd.most_common(30))
if __name__=='__main__': main()
