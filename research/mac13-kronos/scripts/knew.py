import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    team={c['id']:c['team'] for c in m['champions']}
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
    P=C[a]; sc=o['gems']
    need=1000-sc[w][min(r0,len(sc[w])-1)]
    last=None
    for r in range(min(r0,len(P['seenBy'])-1),-1,-1):
        if P['seenBy'][r]:
            last=r; break
    if last is None: return ('never',)
    known=P['gems'][last]
    return ('seen', r0-last, known>=need, known, need)
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    print(collections.Counter(x[0] for x in R))
    S=[x for x in R if x[0]=='seen']
    ag=sorted(x[1] for x in S); n=len(ag); print('rounds since last seen before channel start',[ag[int(n*q)] for q in (.1,.25,.5,.75,.9)])
    print('last-seen bag already >= need:',sum(x[2] for x in S),'of',n)
    print('median known',statistics.median(x[3] for x in S),'need',statistics.median(x[4] for x in S))
