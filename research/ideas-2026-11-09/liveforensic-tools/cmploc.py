import os
import pickle, collections, numpy as np, sys
res=pickle.load(open(sys.argv[1],'rb')); X,Y=sys.argv[2],sys.argv[3]
D=collections.defaultdict(dict)
for b,m,s,f in res:
    for tag in (X,Y):
        if f'lf-{tag}-' in b: D[tag][(m,s,b.split('-o29')[1][0] if '-o29' in b else b.split('-')[-2])]=f
ks=sorted(set(D[X])&set(D[Y])); print(len(ks))
for x in ['lock_us_e','lockhit_op_e','tblk_op_e','tcan_op_lock_e','tcan_op_manual_e','op400','op600','us600','op800','us800','gold600op','gold600us','lock_op_e','lockhit_us_e','rounds']:
    a=np.array([D[X][k].get(x,0) for k in ks]); c=np.array([D[Y][k].get(x,0) for k in ks])
    print(f"{x:<18} {X} {a.mean():8.2f} {Y} {c.mean():8.2f}  diff {np.mean(c-a):+7.2f} ± {1.96*np.std(c-a)/np.sqrt(len(ks)):.2f}")
