"""Paired per-game metric differences, arm batch vs mirror batch (both: T = bot 0's team = the arm/rm2b).
usage: armdiff.py ANA_MIRROR ANA_ARM [extra metric modules]"""
import beh, json, sys, os, math
from multiprocessing import Pool
def keyed(A):
    idx=json.load(open(A+'/index.json'))['games']; out={}
    for g in idx:
        s=os.path.basename(g['source']); stem=s.split('-',1)[1].rsplit('.',1)[0]
        o=stem.rsplit('-',1)[1]; out[stem]=(A+'/'+g['dir'], 0 if o=='12' else 1)
    return out
def run(j):
    k,(da,Ta),(db,Tb)=j
    try: return (k, beh.metrics(da,Ta), beh.metrics(db,Tb))
    except Exception: return (k,None,None)
KEYS=['win','gold_us','gold_op','gold600_us','gold600_op','capg_us','capg_op','death_us','death_op','dgems_us','dgems_op','rounds','tribg_us','tribg_op','trib100g_us','trib100g_op','tstart100_us','tstart100_op','death_us','death_op','dgems_us','dgems_op','death40_us','death40_op','death100_us','death100_op','carry100_us','carry100_op','carry150_us','carry150_op','maxbag_us','maxbag_op','lockcut_us','lockcut_op','tcan_stun_us','tcan_stun_op','tcan_manual_us','tcan_manual_op']
if __name__=='__main__':
    a=keyed(sys.argv[1]); b=keyed(sys.argv[2]); ks=sorted(set(a)&set(b))
    with Pool(32) as p: res=[r for r in p.map(run,[(k,a[k],b[k]) for k in ks],chunksize=8) if r[1]]
    print('paired games',len(res))
    for m in KEYS:
        d=[rb.get(m,0)-ra.get(m,0) for _,ra,rb in res]; n=len(d); mu=sum(d)/n
        sd=math.sqrt(sum((x-mu)**2 for x in d)/(n-1)); base=sum(ra.get(m,0) for _,ra,_ in res)/n
        print(f'{m:16} mirror {base:8.2f}  arm-mirror {mu:+8.3f} ±{1.96*sd/math.sqrt(n):.3f}')
