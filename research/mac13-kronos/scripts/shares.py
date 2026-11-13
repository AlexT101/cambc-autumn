import json,gzip,glob,collections
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    if sum(1 for c in m['champions'] if c['name']=='Prism')!=2: return None
    c=collections.Counter()
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k']!='capture': continue
        sh=e['shares']; tot=sum(s[1] for s in sh)
        if tot==0: continue
        pr=[s for s in sh if names[s[0]]=='Prism']
        ph='early' if e['r']<=300 else 'late'
        if pr and len(sh)==1: c[(ph,'prism_solo')]+=tot
        elif pr: c[(ph,'prism_shared_prism_part')]+=pr[0][1]; c[(ph,'prism_shared_others_part')]+=tot-pr[0][1]
        else: c[(ph,'others')]+=tot
    return c
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=8) if x]
    t=collections.Counter()
    for x in R: t.update(x)
    for k in sorted(t): print(k, round(t[k]/len(R)/2,1),'per team-game')
