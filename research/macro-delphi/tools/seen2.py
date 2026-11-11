import json,gzip,glob,sys,collections,zipfile
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]; ROOT='/home/ubuntu/wt/macro-o4/'
def cheb(a,b):
    if None in a or None in b: return 99
    return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    src=M['sources'][0]['source']; z=zipfile.ZipFile(ROOT+src); D={}
    for t,f in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        for line in z.read(f).decode(errors='replace').splitlines():
            p=line.split()
            if len(p)>=4 and p[0]=='D': D[(int(p[2]),int(p[1]))]=p[3]
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    C={c['id']:c for c in R['champions']}
    out=collections.Counter(); seenpair=set()
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or e.get('by') is None or names.get(e['by'])!='Prism': continue
        v=e['v']; k=e['by']; r=e['r']
        if 'linked' in e: 
            key=(r,min(v,e['linked']))
            if key in seenpair: continue
            seenpair.add(key)
        i=ri.get(r-4)
        if i is None: continue
        if k not in C[v]['sees'][i]: out['unseen']+=1; continue
        dd=cheb((C[v]['x'][i],C[v]['y'][i]),(C[k]['x'][i],C[k]['y'][i]))
        seq=''.join(D.get((v,rr),'.') for rr in range(r-4,r))
        out['seen']+=1
        out['dec4:'+seq[0]]+=1
        out['dec1:'+seq[-1]]+=1
        out['d4:%d'%min(dd,9)]+=1
        # numbers within 8 of victim at r-4
        at=(C[v]['x'][i],C[v]['y'][i])
        na=sum(1 for c in C if team[c]==team[v] and c!=v and C[c]['alive'][i] and cheb(at,(C[c]['x'][i],C[c]['y'][i]))<=8)
        ne=sum(1 for c in C if team[c]!=team[v] and C[c]['alive'][i] and cheb(at,(C[c]['x'][i],C[c]['y'][i]))<=8)
        out['adv:%+d'%max(-3,min(3,na+1-ne))]+=1
        # victim focus ratio of its own prism vs killer
        P=[c for c in C if team[c]==team[v] and names[c]=='Prism' and C[c]['alive'][i]]
        if P: out['ourP/theirs:%s'%('<0.8' if C[P[0]]['foc'][i]<0.8*C[k]['foc'][i] else '<1.25' if C[P[0]]['foc'][i]<1.25*C[k]['foc'][i] else '>1.25')]+=1
        else: out['ourP dead']+=1
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.Counter()
    for o in ProcessPoolExecutor(32).map(one,dirs): agg.update(o)
    for k in sorted(agg): print(k, agg[k])
if __name__=='__main__': main()
