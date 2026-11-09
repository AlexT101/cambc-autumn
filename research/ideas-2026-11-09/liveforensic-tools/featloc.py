import os
# features of local batch games: python featloc.py ANA_DIR out.pkl batchdir...
import gzip, json, pickle, sys, os, re
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0,os.path.dirname(__file__))
ANA=Path(sys.argv[1]); OUT=sys.argv[2]; BATCH=[str(Path(b).resolve()) for b in sys.argv[3:]]
idx=json.load(open(ANA/'index.json'))['games']
ROOT=Path('/home/ubuntu/cambc-autumn')
import importlib.util
spec=importlib.util.spec_from_file_location('feat',os.path.join(os.path.dirname(__file__),'feat_core.py')); fc=importlib.util.module_from_spec(spec); spec.loader.exec_module(fc)
def job(g):
    src=str((ROOT/g['source']).resolve()) if not os.path.isabs(g['source']) else g['source']
    b=[x for x in BATCH if src.startswith(x)]
    if not b: return None
    m=re.search(r'^\d+-(.+)-(12|21)\.repl26a$',os.path.basename(src))
    T=0 if m.group(2)=='12' else 1
    f=fc.features(ANA/g['dir'],T)
    return (os.path.basename(b[0]),m.group(1),'a' if T==0 else 'b',f)
if __name__=='__main__':
    with Pool(12) as P: res=[r for r in P.map(job,idx,chunksize=8) if r]
    pickle.dump(res,open(OUT,'wb')); print(len(res))
