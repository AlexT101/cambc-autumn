import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    w=m['result']['winner']
    starts={}; rows=[]
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k'] not in ('tribute_start','tribute_end','tribute_cancel','death'): continue
        a=e.get('a', e.get('v'))
        if names.get(a)!='Prism': continue
        if e['k']=='tribute_start': starts[a]=e
        elif a in starts:
            s=starts.pop(a)
            res=e['k'] if e['k']!='tribute_cancel' else 'cancel_'+e.get('cause','')
            rows.append((team[a]==w, s['gems'], s['dur'], e['r']-s['r'], res, s['r']))
    return rows
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[r for x in p.map(one,fs,chunksize=8) if x for r in x]
    for lo,hi in ((1,50),(50,150),(150,300),(300,500),(500,2000)):
        sel=[r for r in R if lo<=r[1]<hi]
        c=collections.Counter(r[4] for r in sel); n=len(sel)
        print('bag %d-%d'%(lo,hi), n, {k:round(v/n,3) for k,v in c.most_common()}, 'mean turns in before cancel', round(statistics.mean([r[3] for r in sel if r[4]!='tribute_end'] or [0]),1))
