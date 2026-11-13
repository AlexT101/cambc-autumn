# Deaths per 1,000 alive champion-rounds by ground band (side fraction from the spawns), by body type, r<=500.
import json,gzip,glob,collections
from multiprocessing import Pool
def band(p,a,b):
    da=max(abs(p[0]-a[0]),abs(p[1]-a[1])); db=max(abs(p[0]-b[0]),abs(p[1]-b[1]))
    f=da/max(1,da+db)
    return 'own' if f<0.4 else 'mid' if f<=0.6 else 'enemy'
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz')); T=min(len(o['round']),501)
    sp={}
    for c in o['champions']:
        sp.setdefault(c['team'],(c['x'][0],c['y'][0]))
    kind=lambda n: 'pair' if n in('Cassi','Issac') else 'Prism' if n=='Prism' else 'other'
    rounds=collections.Counter(); deaths=collections.Counter()
    for c in o['champions']:
        t=c['team']; k=kind(names[c['id']])
        for r in range(T):
            if c['alive'][r] and c['x'][r] is not None:
                rounds[(k,band((c['x'][r],c['y'][r]),sp[t],sp[1-t]))]+=1
    tm={c['id']:c['team'] for c in m['champions']}
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['r']>500: break
        if e['k']=='death':
            v=e['v']; t=tm[v]; k=kind(names[v])
            deaths[(k,band(e['at'],sp[t],sp[1-t]))]+=1 if k!='pair' else 0.5
    return rounds,deaths
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    Ro=collections.Counter(); D=collections.Counter()
    for r,d in R: Ro.update(r); D.update(d)
    for k in ('pair','Prism','other'):
        print(k,{b:(round(1000*D[(k,b)]/max(1,Ro[(k,b)]),2),Ro[(k,b)]) for b in ('own','mid','enemy')})
