# During each giant (200+) winning enemy channel: rounds where a loser champion SEES the channeller,
# its distance, its branch, cooldowns and carried consumables.
import json,gzip,glob,collections,statistics,zipfile
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    team={c['id']:c['team'] for c in m['champions']}; names={c['id']:c['name'] for c in m['champions']}
    w=m['result']['winner']
    starts={}; win=None
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['k']=='tribute_start': starts[e['a']]=e
        elif e['k']=='tribute_end':
            s=starts.pop(e['a'],None)
            if team[e['a']]==w and e['total']>=1000 and s and s['gems']>=200: win=(e['a'],s['r'],e['r'],s['gems'])
        elif e['k']=='tribute_cancel': starts.pop(e['a'],None)
    if not win: return None
    a,r0,r1,g=win
    o=json.load(gzip.open(d+'/rounds.json.gz')); T=len(o['round']); r1=min(r1,T-1)
    P=[c for c in o['champions'] if c['id']==a][0]
    z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    txt=z.read('team-%s.stdout'%('ab'[1-w])).decode('latin1')
    br={}
    for line in txt.splitlines():
        if line.startswith('D '):
            p=line.split()
            r=int(p[1])
            if r0<=r<=r1: br[(r,int(p[2]))]=p[3]
    rows=[]; seen_any=0
    for c in o['champions']:
        if c['team']==w: continue
        for r in range(r0,r1+1):
            if not c['alive'][r] or c['x'][r] is None: continue
            if a in (c['sees'][r] or []):
                dd=max(abs(c['x'][r]-P['x'][r]),abs(c['y'][r]-P['y'][r]))
                rows.append((names[c['id']],dd,br.get((r,c['id']),'?'),c['cd0'][r],c['cd1'][r],tuple(c['cons'][r]),c['hp'][r]/max(1,c['maxHp'][r])))
    return (r1-r0,rows)
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    print('channels',len(R),'with any seen round',sum(1 for x in R if x[1]))
    rows=[r for x in R for r in x[1]]
    print('seen champion-rounds',len(rows))
    print('by champion',collections.Counter(r[0] for r in rows).most_common())
    print('dist',collections.Counter(min(r[1],9) for r in rows).most_common())
    print('branch',collections.Counter(r[2] for r in rows).most_common(15))
    print('branch dist<=4',collections.Counter(r[2] for r in rows if r[1]<=4).most_common(15))
    print('cd0 zero share',sum(r[3]==0 for r in rows)/len(rows),'cd1 zero',sum(r[4]==0 for r in rows)/len(rows))
    print('cons',collections.Counter(r[5] for r in rows).most_common(6))
    print('hp<0.5 share',sum(r[6]<0.5 for r in rows)/len(rows))
