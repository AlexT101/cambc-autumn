import zipfile, re, sys, os, json, gzip
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
A='replays/.analysis'
def one(g):
    try:
        d=os.path.join(A,g['dir']); meta=json.load(open(os.path.join(d,'meta.json'))); z=zipfile.ZipFile(g['source'])
    except Exception: return None
    cn={c['id']:c['name'] for c in meta['champions']}; c=Counter()
    for nm in z.namelist():
        if nm.endswith('.stdout'):
            for m in D.finditer(z.read(nm)):
                cid=int(m.group(2))
                if cn.get(cid)=='Willow': c[m.group(3).decode()]+=1
    return c
if __name__=='__main__':
    idx=json.load(open(A+'/index.json')); gs=[g for g in idx['games'] if 'mirdbg' in g['source']][:400]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for c in ex.map(one,gs,chunksize=4):
            if c: tot.update(c)
    s=sum(tot.values()); print('Willow D lines',s); print([(k,'%.1f%%'%(100*v/s)) for k,v in tot.most_common(12)])
