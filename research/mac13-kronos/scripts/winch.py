import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
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
    o=json.load(gzip.open(d+'/rounds.json.gz')); C={c['id']:c for c in o['champions']}
    T=len(o['round']); r1=min(r1,T-1)
    P=C[a]; out=collections.Counter()
    mind=99; alive_rounds=0; tot=0; near_rounds=0
    for r in range(r0,r1+1):
        for c in o['champions']:
            if c['team']==w: continue
            tot+=1
            if not c['alive'][r] or c['x'][r] is None: continue
            alive_rounds+=1
            dd=max(abs(c['x'][r]-P['x'][r]),abs(c['y'][r]-P['y'][r]))
            mind=min(mind,dd)
            if dd<=5: near_rounds+=1
    # branches of loser champions during the window
    import zipfile
    z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    txt=z.read('team-%s.stdout'%('ab'[1-w])).decode('latin1')
    br=collections.Counter()
    for line in txt.splitlines():
        if line.startswith('D '):
            p=line.split()
            if r0<=int(p[1])<=r1: br[p[3]]+=1
    return (r1-r0, g, alive_rounds/max(1,tot), mind, near_rounds, br)
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    print('winning giant channels',len(R))
    print('duration median',statistics.median(x[0] for x in R),'gems',statistics.median(x[1] for x in R))
    print('loser alive share in window',round(statistics.mean(x[2] for x in R),3))
    md=sorted(x[3] for x in R); n=len(md); print('loser min dist to channeler quantiles',[md[int(n*q)] for q in (.1,.25,.5,.75,.9)])
    print('windows where a loser champ came within 5:',sum(1 for x in R if x[4]>0))
    br=collections.Counter()
    for x in R: br.update(x[5])
    s=sum(br.values()); print('loser branches in window',{k:round(v/s,3) for k,v in br.most_common(12)})
