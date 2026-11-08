import sys; sys.path.insert(0,'/home/ubuntu/tmp-offload/emblem/tools'); from arch import *
import collections
d=sys.argv[1]; S,U,m=day(d)
for t in ('Intercontinental Fish','Mite','stellar best girl'):
    sel=U['team']==t
    print('=====',t)
    for ty in ('Vesper Vale','Vendetta','Heart of Ruin','Marcella','Issac','Cassi','Prism','Tavi'):
        s=sel&(U['type']==ty); n=s.sum()
        if n<200: continue
        e=U['e'][s]; r=U['r'][s]
        first=collections.Counter(fam(x) for x in e[:,0])
        # capture owned by r300, emblems by r300
        cap300=((e//6==8)&(r<=300)).any(1).mean(); cap200=((e//6==8)&(r<=200)).any(1).mean()
        n300=(r<=300).sum(1).mean()
        print(f'{ty[:10]:10s} n={n:5d} cap<=200 {cap200:.2f} cap<=300 {cap300:.2f} emb<=300 {n300:.2f} first: '+' '.join(f'{k}:{v/n:.2f}' for k,v in first.most_common(6)))
