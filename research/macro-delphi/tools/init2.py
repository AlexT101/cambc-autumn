import json,gzip,glob,sys,collections,zipfile
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    evs=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    out=collections.Counter(); last={}
    src=M['sources'][0]['source']; z=zipfile.ZipFile('/home/ubuntu/wt/macro-o4/'+src); D={}
    for t,f in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        for line in z.read(f).decode(errors='replace').splitlines():
            p=line.split()
            if len(p)>=4 and p[0]=='D': D[(int(p[2]),int(p[1]))]=p[3]
    w=M['result']['winner']
    n=len(R['round'])
    for x in evs:
        if x['k']!='cast' or x['slot']!=0: continue
        a=x.get('a'); b=x.get('tgt')
        if b is None or names.get(a)!='Prism' or names.get(b)!='Prism': continue
        r=x['r']
        if r-last.get(a,-99)<20: last[a]=r; continue
        last[a]=r
        i=ri.get(r-1)
        if i is None: continue
        Fa,Fb=C[a]['foc'][i],C[b]['foc'][i]; Ha=C[a]['hp'][i]+C[a]['shield'][i]; Hb=C[b]['hp'][i]+C[b]['shield'][i]
        ours=2.5*Fa+2*C[a]['str'][i]>=Hb
        theirs=2.5*Fb+C[b]['str'][i]>=Ha
        bstun=C[b]['cd0'][i]==0
        died=any(not C[a]['alive'][j] for j in range(i,min(n,i+15)))
        killed=any(not C[b]['alive'][j] for j in range(i,min(n,i+15)))
        k=('ourlethal' if ours else 'ournon','theirlethal' if theirs else 'theirnon','tstun' if bstun else 'tcd')
        if k==('ournon','theirlethal','tstun'):
            out['dec',D.get((a,r),'.')]+=1; out['won',team[a]==w]+=1; out['bag', min(C[a]['gems'][i]//100,5)]+=1; out['rnd',r//200]+=1
            out['ratio', round(min(Fa/max(Fb,1),1.5),1)]+=1
        out[k,'n']+=1; out[k,'died']+=died; out[k,'killed']+=killed
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.Counter()
    for o in ProcessPoolExecutor(32).map(one,dirs): agg.update(o)
    print(sorted((k,v) for k,v in agg.items() if k[0] in ('dec','won','bag','rnd','ratio')))
    keys=sorted(set(k[0] for k in agg if isinstance(k[0],tuple)))
    for k in keys:
        n=agg[k,'n']; print(k,n,'initiator died %.2f killed %.2f'%(agg[k,'died']/n,agg[k,'killed']/n))
if __name__=='__main__': main()
