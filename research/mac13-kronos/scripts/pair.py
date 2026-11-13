# Cassi/Issac pair deaths: which body fell, distance between bodies, killer, round, branch, bags.
import json,gzip,glob,collections,statistics,zipfile
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]; w=m['result']['winner']
    team={c['id']:c['team'] for c in m['champions']}; names={c['id']:c['name'] for c in m['champions']}
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz')]
    evpos={id(e):i for i,e in enumerate(ev)}
    o=json.load(gzip.open(d+'/rounds.json.gz')); C={c['id']:c for c in o['champions']}
    z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    br={}
    for side in (0,1):
        for line in z.read('team-%s.stdout'%'ab'[side]).decode('latin1').splitlines():
            if line.startswith('D '):
                p=line.split(); br[(int(p[1]),int(p[2]))]=p[3]
    out=[]; byr=collections.defaultdict(list)
    for e in ev:
        if e['k']=='death' and names[e['v']] in ('Cassi','Issac'): byr[(e['r'],team[e['v']])].append(e)
    pairdeaths=0
    for (r,t),es in byr.items():
        ca=[e for e in es if names[e['v']]=='Cassi']; isq=[e for e in es if names[e['v']]=='Issac']
        if not ca or not isq: continue
        ca,isq=ca[0],isq[0]
        # the body the killing blow hit: the last damaging event before the deaths with a target among the two
        first='?'
        idx=evpos[id(ca)]
        for q in reversed(ev[max(0,idx-60):idx]):
            tg=q.get('tgt'); dm=q.get('dmg')
            tl=tg if isinstance(tg,list) else [tg]
            ids=[]
            for x in tl:
                if isinstance(x,int): ids.append(x)
                elif isinstance(x,list) and x and isinstance(x[0],int): ids.append(x[0])
                elif isinstance(x,dict) and 'id' in x: ids.append(x['id'])
            if dm is not None and (ca['v'] in ids or isq['v'] in ids):
                first='Cassi' if ca['v'] in ids else 'Issac'; break
        dd=max(abs(ca['at'][0]-isq['at'][0]),abs(ca['at'][1]-isq['at'][1]))
        k=ca.get('by'); kn=names.get(k,'camp') if isinstance(k,int) and k in team and team[k]!=t else 'camp'
        bags=ca.get('gems',0)+isq.get('gems',0)
        vic=ca['v'] if first=='Cassi' else isq['v']
        b=next((br.get((r-i,vic)) for i in range(0,4) if br.get((r-i,vic))),'?')
        out.append((first,dd,kn,r,b,bags,t==w,ca['hp'],isq['hp']))
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for r in p.map(one,fs,chunksize=4) if r for x in r]
    print('pair deaths',len(R),'per team-game',round(len(R)/2048,2),'r<=300',sum(x[3]<=300 for x in R))
    print('victim team won',sum(x[6] for x in R))
    print('first body',collections.Counter(x[0] for x in R))
    print('dist between bodies',collections.Counter(min(x[1],12) for x in R).most_common())
    print('killer',collections.Counter(x[2] for x in R).most_common(8))
    print('branch of fallen body',collections.Counter(x[4] for x in R).most_common(8))
    print('bags median',statistics.median(x[5] for x in R),'mean',round(statistics.mean(x[5] for x in R),1))
    print('sample hp',R[:5])
