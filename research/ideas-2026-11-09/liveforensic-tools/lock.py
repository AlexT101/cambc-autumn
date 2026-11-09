import os
import pickle, collections, math
SC=os.path.expanduser('~/tmp-offload/liveforensic/')+''
cells,mc=pickle.load(open(SC+'cells.pkl','rb')); F=pickle.load(open(SC+'feat.pkl','rb'))
A=[86,87,89,95]; B=[91,93]
W=lambda v,k: cells[k][v]['result']=='win'
def bucket(x):
    return '0' if x==0 else ('0-1' if x<1 else ('1-3' if x<3 else ('3-6' if x<6 else '6+')))
agg=collections.defaultdict(lambda:[0,0,0,0,0])
for k in cells:
    la=sum(F[(v,k)].get('lock_us_e',0) for v in A)/len(A)
    ha=sum(F[(v,k)].get('lockhit_op_e',0) for v in A)/len(A)
    sa=sum(W(v,k) for v in A)/len(A); sb=sum(W(v,k) for v in B)/len(B)
    for g in [('locksA',bucket(la)),('hitsA',bucket(ha/3)),('opp/locks',k[2],bucket(la)),('cls/locks',mc[k[0]],bucket(la))]:
        a=agg[g]; a[0]+=1; a[1]+=sa; a[2]+=sb
for g,(n,sa,sb,_,_) in sorted(agg.items()):
    # rough SE: flips ~ 32% per pair -> per-cell diff var ~ 0.32*(1/4+1/2)/... use empirical
    print(f"{str(g):<30} n{n:4d} A {100*sa/n:5.1f} B {100*sb/n:5.1f} B-A {100*(sb-sa)/n:+5.1f} net {sb-sa:+.1f}")
