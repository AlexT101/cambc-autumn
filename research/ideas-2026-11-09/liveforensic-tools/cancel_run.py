import os
import json, pickle, re, sys
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import cancel
if __name__=='__main__':
    G=Path('/home/ubuntu/tmp-offload/handoff/gate'); ROOT=Path('/home/ubuntu/cambc-autumn')
    cells,mc=pickle.load(open(os.path.expanduser('~/tmp-offload/liveforensic/cells.pkl'),'rb'))
    idx=json.load(open(G/'analysis/index.json'))['games']; by={str((ROOT/g['source']).resolve()):g['dir'] for g in idx}
    cls=sys.argv[1]
    jobs={}
    for v in (89,91):
        for k in cells:
            if mc[k[0]]!=cls: continue
            p=str((G/'raw'/f'v{v}-r2'/('inte' if k[2]=='fish' else 'mite')/f'{k[0]}-{k[1]}.repl26a').resolve())
            jobs.setdefault(v,[]).append((str(G/'analysis'/by[p]),0 if k[1]=='a' else 1))
    lidx=json.load(open('/home/ubuntu/tmp-offload/liveforensic/ana/index.json'))['games']
    for g in lidx:
        m=re.search(r'lf-(c2[78])-o29[FM].*/\d+-(.+)-(12|21)\.repl26a$',g['source'])
        if m and mc.get(m.group(2).replace('-','_'))==cls:
            jobs.setdefault(m.group(1),[]).append(('/home/ubuntu/tmp-offload/liveforensic/ana/'+g['dir'],0 if m.group(3)=='12' else 1))
    with Pool(12) as P:
        for v,js in jobs.items():
            rows=[r for o in P.map(cancel.scan,js) for r in o]
            cancel.summ(f'{v} {cls} ({len(js)} games)',rows)
