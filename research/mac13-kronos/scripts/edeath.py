# Deaths r<=300 in the mirror: victim, killer, cause, gems, victim's last branch, side.
import json,gzip,glob,collections,statistics,zipfile
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]; w=m['result']['winner']
    team={c['id']:c['team'] for c in m['champions']}; names={c['id']:c['name'] for c in m['champions']}
    z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    br={}
    for side in (0,1):
        for line in z.read('team-%s.stdout'%'ab'[side]).decode('latin1').splitlines():
            if line.startswith('D '):
                p=line.split(); r=int(p[1])
                if r<=300: br[(r,int(p[2]))]=p[3]
    out=[]
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['r']>300: break
        if e['k']=='death':
            v=e['v']; k=e.get('by')
            kn=names.get(k,'camp') if isinstance(k,int) and k in team and team[k]!=team[v] else 'camp/other'
            last=[br.get((e['r']-i,v)) for i in range(0,6)]
            out.append((names[v],kn,e.get('cause'),e.get('gems',0),last,team[v]==w,e['r']))
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for r in p.map(one,fs,chunksize=4) if r for x in r]
    print('deaths r<=300',len(R),'victim team lost',sum(not x[5] for x in R))
    print('victims',collections.Counter(x[0] for x in R).most_common(10))
    print('killers',collections.Counter(x[1] for x in R).most_common(10))
    print('victim->killer',collections.Counter((x[0],x[1]) for x in R).most_common(12))
    print('cause',collections.Counter(x[2] for x in R).most_common())
    print('last branch at death',collections.Counter(next((b for b in x[4] if b),'?') for x in R).most_common(10))
    print('branches 5 rounds before',collections.Counter(x[4][5] for x in R).most_common(10))
    print('round quartiles',sorted(x[6] for x in R)[len(R)//4::len(R)//4])
