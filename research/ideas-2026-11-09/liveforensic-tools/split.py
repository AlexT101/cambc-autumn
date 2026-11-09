import os
import pickle, math, collections
cells,mc=pickle.load(open(os.path.expanduser('~/tmp-offload/liveforensic/')+'cells.pkl','rb'))
A=[86,87,89,95]; B=[91,93]
def w(r): return r['result']=='win'
def score(c,vs): return sum(w(c[v]) for v in vs)/len(vs)
def feats(k,c):
    r=c[86]
    hor_us='Heart of Ruin' in r['our_picks']; hor_them='Heart of Ruin' in r['opp_picks']
    rounds=sorted(c[v]['rounds'] for v in A+B)
    med=rounds[len(rounds)//2]
    return {'opp':k[2],'cls':mc[k[0]],'hor':('us' if hor_us else '')+('them' if hor_them else '') or 'none',
            'willow':'W' if 'Willow' in r['our_picks'] else '-','len':'>1200' if med>1200 else ('600-1200' if med>600 else '<600'),
            'npick':len(r['our_picks'])}
def report(key):
    agg=collections.defaultdict(lambda:[0,0.0,0.0])
    for k,c in cells.items():
        if not all(v in c for v in A+B): continue
        f=feats(k,c); g=key(f)
        a=agg[g]; a[0]+=1; a[1]+=score(c,A); a[2]+=score(c,B)
    tot=[0,0,0]
    for g,(n,sa,sb) in sorted(agg.items(),key=lambda x:str(x[0])):
        print(f"  {str(g):<28} n{n:4d}  A {100*sa/n:5.1f}  B {100*sb/n:5.1f}  B-A {100*(sb-sa)/n:+5.1f}  (net games {sb-sa:+.1f})")
for name,key in [('opp',lambda f:f['opp']),('cls',lambda f:f['cls']),('hor',lambda f:f['hor']),('willow',lambda f:f['willow']),
                 ('len',lambda f:f['len']),('cls x len',lambda f:(f['cls'],f['len'])),('opp x hor',lambda f:(f['opp'],f['hor'])),('npick',lambda f:f['npick'])]:
    print(name); report(key)
# consistent cells
cnt=collections.Counter()
for k,c in cells.items():
    if not all(v in c for v in A+B): continue
    sa=score(c,A); sb=score(c,B)
    if sa==1 and sb==0: cnt['A all win, B both lose']+=1
    if sa==0 and sb==1: cnt['A all lose, B both win']+=1
print(cnt)
