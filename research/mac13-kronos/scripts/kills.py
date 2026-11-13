import json,gzip,glob,collections
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    c=collections.Counter()
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k']!='death' or e.get('linked'): continue
        v=names[e['v']]; k=names.get(e.get('by'),'camp')
        c[('victim_prism' if v=='Prism' else 'victim_other', 'by_prism' if k=='Prism' else 'by_other' if k!='camp' else 'camp')]+=1
        c[('gems_to', 'by_prism' if k=='Prism' else 'other')]+=e.get('gemsTo',0) or 0
    return c
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=8) if x]
    t=collections.Counter()
    for x in R: t.update(x)
    for k in sorted(t): print(k, round(t[k]/len(R),2), 'per game')
