"""Paired behaviour of CAND (bot 0) between an arm batch and the mirror batch on the same games.
usage: pair.py ARM_ANA MIR_ANA"""
import cmb, hordash, json, os, sys, collections, math
from multiprocessing import Pool
def jobs(A):
    idx=json.load(open(A+'/index.json'))['games']; out={}
    for g in idx:
        b=os.path.basename(g['source']); o=b.rsplit('-',1)[1].split('.')[0]
        key=b.split('-',1)[1]  # drop the batch index
        out[key]=(A+'/'+g['dir'], 0 if o=='12' else 1)
    return out
def one(j):
    d,T=j
    try:
        f=cmb.cm(d,T); h=hordash.dashes(d,T)
    except Exception: return None
    for side in ('us','op'):
        L=[x for x in h if x[0]==side]
        f['hd_'+side]=len(L); f['hdlo_'+side]=sum(1 for x in L if x[1]<0.6)
        f['hdlo_die_'+side]=sum(x[2] for x in L if x[1]<0.6); f['hd_kill_'+side]=sum(x[3] for x in L)
        f['hdhi_die_'+side]=sum(x[2] for x in L if x[1]>=0.6)
    return f
if __name__=='__main__':
    a=jobs(sys.argv[1]); b=jobs(sys.argv[2]); keys=sorted(set(a)&set(b))
    with Pool(24) as p:
        fa=p.map(one,[a[k] for k in keys],chunksize=8); fb=p.map(one,[b[k] for k in keys],chunksize=8)
    pairs=[(x,y) for x,y in zip(fa,fb) if x and y]
    allk=sorted(set().union(*[set(x)|set(y) for x,y in pairs]))
    print('n pairs',len(pairs))
    print('metric'.ljust(20)+'arm'.rjust(12)+'mirror'.rjust(12)+'diff'.rjust(10)+'±95'.rjust(9))
    for k in allk:
        d=[x.get(k,0)-y.get(k,0) for x,y in pairs]; m=sum(d)/len(d)
        sd=math.sqrt(sum((v-m)**2 for v in d)/max(1,len(d)-1))/math.sqrt(len(d))
        print(k.ljust(20)+f'{sum(x.get(k,0) for x,_ in pairs)/len(pairs):12.3f}{sum(y.get(k,0) for _,y in pairs)/len(pairs):12.3f}{m:10.3f}{1.96*sd:9.3f}')
