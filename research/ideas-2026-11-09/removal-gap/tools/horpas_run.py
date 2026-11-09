import horpas, json, os, sys, collections
from multiprocessing import Pool
import cmb_run
def run(j):
    try: return (j[0], horpas.hp(j[1], j[2]))
    except Exception: return (j[0], {})
if __name__=='__main__':
    jobs=cmb_run.live(['v87-r2','v88-r2','v89-r2'])
    for a in sys.argv[1:]: jobs+=cmb_run.loc(a,'local:'+os.path.basename(a))
    with Pool(32) as p: res=p.map(run,jobs,chunksize=8)
    G=collections.defaultdict(collections.Counter)
    for k,c in res: G[k].update(c)
    for k in sorted(G):
        c=G[k]
        for s in ('us','op'):
            if c['w_'+s]: print(f"{k:22} {s} HoR bodies {c['n_'+s]:5d} passive(dmg-wt) {c['p_'+s]/c['w_'+s]:.3f} dmg share <0.5hp {c['lo_'+s]/c['w_'+s]:.3f} deaths/body {c['deaths_'+s]/c['n_'+s]:.2f} kills/body {c['kills_'+s]/c['n_'+s]:.2f}")
