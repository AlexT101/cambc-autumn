import hordash, cmb_run, sys, os, collections
from multiprocessing import Pool
import hordash_live as HL
if __name__=='__main__':
    jobs=[]
    for a in sys.argv[1:]:
        jobs+=cmb_run.loc(a,'loc:'+os.path.basename(a)+':bot0',0)
    with Pool(24) as p: res=p.map(HL.run,jobs,chunksize=8)
    G=collections.defaultdict(list)
    for k,o in res: G[k]+=o
    HL.report(G)
